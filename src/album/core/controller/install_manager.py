from contextlib import ExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.install_manager import IInstallManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.controller.environment_manager import EnvironmentManager
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import remove_link
from album.core.utils.operations.resolve_operations import (
    build_resolve_string,
    clean_resolve_tmp,
    dict_to_coordinates,
)
from album.core.utils.operations.solution_operations import (
    get_deploy_dict,
    get_parent_dict,
)
from album.environments.utils.subcommand import SubProcessError
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


class InstallManager(IInstallManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def install(
        self,
        solution_to_resolve: str,
        allow_recursive: bool = False,
        argv: Optional[List[str]] = None,
    ) -> ISolution:
        # this needs to happen before any (potentially not completely installed) solution is resolved
        self.clean_unfinished_installations()

        resolve_result = self.album.collection_manager().resolve_and_load(
            solution_to_resolve
        )
        self._install_loaded_resolve_result(
            resolve_result, parent=False, allow_recursive=allow_recursive
        )

        return resolve_result.loaded_solution()

    def _resolve_result_is_installed(self, resolve_result: ICollectionSolution) -> bool:
        if resolve_result.database_entry():  # we know the solution is in the collection
            # not installed when another album process removed it from the collection
            # since it was resolved
            return self.album.solutions().is_installed(
                resolve_result.catalog(), resolve_result.coordinates()
            )
        return False

    def _skip_installed(
        self, resolve_result: ICollectionSolution, parent: bool
    ) -> bool:
        # an installed solution is skipped, not reinstalled: with a warning when it
        # was requested directly, silently when it is the parent of another solution
        if not self._resolve_result_is_installed(resolve_result):
            return False
        if not parent:
            module_logger().warning(
                'Solution "%s" already installed. Skipping...'
                % resolve_result.loaded_solution().coordinates().name()
            )
        return True

    def _lock_for_installation(
        self, resolve_result: ICollectionSolution, locks: ExitStack
    ) -> None:
        """Wait for the lock of the solution, and hold it until the locks are released.

        Another album process or thread installing or uninstalling the same solution
        holds it, or one installing a solution into its environment.
        """
        lock = self.album.solutions().get_solution_lock(
            resolve_result.catalog(), resolve_result.coordinates()
        )
        if lock.is_held_by_current_thread():
            # this thread is installing it already, as a child of itself
            raise ValueError(
                'Solution "%s" cannot be its own parent!' % resolve_result.coordinates()
            )
        locks.enter_context(lock)

    def _install_loaded_resolve_result(
        self,
        resolve_result: ICollectionSolution,
        parent: bool = False,
        allow_recursive: bool = False,
    ) -> None:
        if not resolve_result.catalog():
            raise RuntimeError(
                "Solution cannot be installed without being associated with a catalog!"
            )

        # checked before waiting for the lock: installing an installed solution does not
        # wait for album processes installing a solution into its environment
        if self._skip_installed(resolve_result, parent):
            return

        # the locks of the solution and of its parents are held until it is installed
        with ExitStack() as locks:
            self._lock_for_installation(resolve_result, locks)
            self._install_holding_lock(resolve_result, parent, allow_recursive, locks)

    def _install_holding_lock(
        self,
        resolve_result: ICollectionSolution,
        parent: bool,
        allow_recursive: bool,
        locks: ExitStack,
    ) -> None:
        # checked again: while this one waited for the lock, another album process might
        # have installed the solution, or failed to and removed the solution files
        if self._skip_installed(resolve_result, parent):
            return
        # holding the lock, no other installation of the solution is in progress: an
        # unfinished one was left by an album process that ended before finishing it
        self._clean_unfinished_installation(
            resolve_result.catalog(), resolve_result.coordinates()
        )
        if not Path(resolve_result.path()).exists():
            self.album.collection_manager().retrieve_and_load_resolve_result(
                resolve_result
            )
            self.album.solutions().set_cache_paths(
                resolve_result.loaded_solution(), resolve_result.catalog()
            )

        module_logger().debug(
            'solution loaded from catalog "%s": %s...'
            % (
                resolve_result.catalog().name(),
                str(resolve_result.loaded_solution().coordinates()),
            )
        )
        if not parent:
            module_logger().info(
                'Installing "%s"...'
                % resolve_result.loaded_solution().coordinates().name()
            )
        else:
            module_logger().info(
                'Installing parent solution "%s"...'
                % resolve_result.loaded_solution().coordinates().name()
            )

        self._register(resolve_result)

        if not parent:
            if resolve_result.catalog().is_cache():
                # always clean after registration to a catalog!
                clean_resolve_tmp(self.album.configuration().tmp_path())

        # mark as "installation unfinished"
        self.album.solutions().set_installation_unfinished(
            resolve_result.catalog(), resolve_result.coordinates()
        )

        try:
            # download the resources before the environment is built, so a broken resource
            # fails early. The install routine can use them.
            self.album.download_manager().download_resources(resolve_result)

            # run installation recursively
            self._install_active_solution(resolve_result, locks, allow_recursive)

            # mark as installed and remove "installation unfinished"
            self.album.solutions().set_installed(
                resolve_result.catalog(), resolve_result.coordinates()
            )
        except BaseException:
            # also when interrupted (e.g. Ctrl+C): what was installed is removed right
            # away, still holding the lock, instead of by the next installation
            self._remove_failed_installation(resolve_result)
            raise
        if parent:
            module_logger().info(
                "Installed parent solution %s!" % resolve_result.coordinates().name()
            )
        else:
            module_logger().info(
                "Installed %s! Learn more about the solution by calling `album info %s`."
                % (resolve_result.coordinates().name(), resolve_result.coordinates())
            )

    def _register(self, resolve_result: ICollectionSolution):
        # register in collection
        if resolve_result.catalog().is_cache():
            # a cache catalog is living in the collection so no need to update, we can add it directly
            self.album.solutions().add_to_cache_catalog(resolve_result)
        else:
            # update the collection holding the solution entry
            self._update_in_collection_index(resolve_result)

        self.album.collection_manager().get_collection_index()

        db_entry = (
            self.album.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                resolve_result.catalog().catalog_id(), resolve_result.coordinates()
            )
        )

        if db_entry is None:
            raise RuntimeError(
                "Solution not found in collection index. Cannot register solution!"
            )

        resolve_result.set_database_entry(db_entry)

    def _remove_parent(self, resolve_result: ICollectionSolution):
        self.album.solutions().remove_parent(
            resolve_result.catalog(), resolve_result.coordinates()
        )

    def _update_in_collection_index(self, resolve_result: ICollectionSolution):
        # update the solution in the collection
        self.album.solutions().update_solution(
            resolve_result.catalog(),
            resolve_result.coordinates(),
            get_deploy_dict(resolve_result.loaded_solution()),
        )

    def _install_active_solution(
        self,
        collection_solution: ICollectionSolution,
        locks: ExitStack,
        allow_recursive: bool = False,
    ) -> Optional[ICollectionSolution]:
        parent_resolve_result = None

        parent = get_parent_dict(collection_solution.loaded_solution())
        if parent:
            # install dependencies first. Recursive call to install with dependencies
            try:
                parent_resolve_result = self._install_parent(
                    parent,
                    collection_solution.loaded_solution().setup().album_api_version,
                    collection_solution.coordinates(),
                    locks,
                    allow_recursive=allow_recursive,
                )
            except Exception as e:
                module_logger().error("Exception when installing parent:")
                raise e

            if parent_resolve_result:
                db_entry_parent = parent_resolve_result.database_entry()
                if db_entry_parent is None:
                    raise RuntimeError(
                        "Parent solution not found in collection index. Cannot install parent solution!"
                    )

                db_entry_solution = collection_solution.database_entry()
                if db_entry_solution is None:
                    raise RuntimeError(
                        "Solution not found in collection index. Cannot install solution!"
                    )

                self.album.solutions().set_parent(
                    db_entry_parent,
                    db_entry_solution,
                )
            else:
                self._remove_parent(collection_solution)

            db_entry = (
                self.album.collection_manager()
                .get_collection_index()
                .get_solution_by_catalog_grp_name_version(
                    collection_solution.catalog().catalog_id(),
                    collection_solution.coordinates(),
                )
            )
            if db_entry is None:
                raise RuntimeError(
                    "Solution not found in collection index. Cannot install parent solution!"
                )

            collection_solution.set_database_entry(db_entry)
        else:
            self.album.environment_manager().install_environment(
                collection_solution, allow_recursive
            )

        # ensure cache paths exist
        collection_solution.loaded_solution().installation().internal_cache_path().mkdir(
            exist_ok=True, parents=True
        )
        collection_solution.loaded_solution().installation().user_cache_path().mkdir(
            exist_ok=True, parents=True
        )
        collection_solution.loaded_solution().installation().data_path().mkdir(
            exist_ok=True, parents=True
        )
        collection_solution.loaded_solution().installation().app_path().mkdir(
            exist_ok=True, parents=True
        )

        self._run_solution_install_routine(collection_solution)
        return parent_resolve_result

    def _install_parent(
        self,
        parent_dict: Dict[str, Any],
        api_version: str,
        child_coordinates: ICoordinates,
        locks: ExitStack,
        allow_recursive: bool = False,
    ) -> ICollectionSolution:
        resolve_solution = build_resolve_string(parent_dict)
        resolve_result_parent = self.album.collection_manager().resolve_and_load(
            resolve_solution
        )

        # check whether child_coordinates are resolved_parent coordinates
        if resolve_result_parent.coordinates() == child_coordinates:
            raise ValueError(
                "Parent solution cannot be the same as the child solution!"
            )

        # check whether API version is compatible
        if (
            api_version
            != resolve_result_parent.loaded_solution().setup().album_api_version
        ):
            raise RuntimeError(
                "API version of parent solution (%s) is not compatible "
                "with the requested API version (%s)."
                " Please update the parent solution."
                % (
                    resolve_result_parent.loaded_solution().setup().album_api_version,
                    api_version,
                )
            )

        # the child is installed into the environment of its parent, which is locked until
        # the child is installed: no album process uninstalls the parent meanwhile
        self._lock_for_installation(resolve_result_parent, locks)

        # recursive installation call. Not failing for already installed solutions. parent set to "True".
        # The child runs in the environment of its parent, so the album-in-album check applies there.
        self._install_holding_lock(
            resolve_result_parent,
            parent=True,
            allow_recursive=allow_recursive,
            locks=locks,
        )
        return resolve_result_parent

    def uninstall(
        self,
        solution_to_resolve: str,
        rm_dep: bool = False,
        argv: Optional[List[str]] = None,
    ) -> None:
        # resolved to know which solution to lock. Holding the lock it is resolved again,
        # as another album process might have uninstalled it while this one waited.
        # A solution that is not found or not installed cannot be uninstalled, that error is for the caller
        resolve_result = self.album.collection_manager().resolve_installed(
            solution_to_resolve
        )
        with self.album.solutions().get_solution_lock(
            resolve_result.catalog(), resolve_result.coordinates()
        ):
            self._uninstall(solution_to_resolve, rm_dep)

    def _uninstall(self, solution_to_resolve: str, rm_dep: bool = False) -> None:
        resolve_result = self.album.collection_manager().resolve_installed(
            solution_to_resolve
        )

        loaded = False
        try:
            self.album.collection_manager().load_resolve_result(resolve_result)
            loaded = True
        except Exception as e:
            # a broken or missing solution file can raise anything when loaded
            module_logger().warning(
                "Cannot load solution (%s). Cannot call uninstall routine. "
                "Proceed without..." % str(e)
            )

        module_logger().info(
            'Uninstalling "%s"...' % resolve_result.coordinates().name()
        )

        db_entry = resolve_result.database_entry()

        if db_entry is None:  # can only happen if resolve_installed method broken
            raise RuntimeError(
                "Solution not found in collection index. Cannot uninstall solution!"
            )

        parent = db_entry.internal()["parent"]

        if db_entry.internal()["children"]:
            children = self._get_child_solution_coordinates(db_entry)

            if children:
                module_logger().info(
                    "The following solutions depend on this installation: %s. Not uninstalling %s..."
                    % (
                        ", ".join([str(child) for child in children]),
                        str(resolve_result.coordinates()),
                    )
                )
                if parent:
                    return

                raise RuntimeError(
                    'Cannot uninstall "%s". Other solution depend on this installation! '
                    "Inspect log for more information!" % resolve_result.coordinates()
                )

        # get the environment. Only the collection entry is needed for this,
        # so the environment is also removed when the solution could not be loaded.
        environment = None
        try:
            environment = self.album.environment_manager().set_environment(
                resolve_result
            )
            if loaded:
                self._run_solution_uninstall_routine(resolve_result)

            if not parent:
                self.album.environment_manager().remove_environment(environment)

        except LookupError:
            # environment might have been deleted manually
            pass
        except SubProcessError:
            # uninstall routine failed
            module_logger().warning("Uninstall routine failed! Proceeding anyways...")
        finally:
            if environment and not parent:
                EnvironmentManager.remove_disc_content_from_environment(environment)

        self._remove_disc_content_from_solution(resolve_result)

        if resolve_result.catalog().is_cache():
            self.album.solutions().remove_solution(
                resolve_result.catalog(), resolve_result.coordinates()
            )
        else:
            self.album.solutions().set_uninstalled(
                resolve_result.catalog(), resolve_result.coordinates()
            )

        if rm_dep:  # remove dependencies (parent of the solution) last
            self._remove_dependencies(resolve_result.loaded_solution(), rm_dep, parent)

        module_logger().info('Uninstalled "%s"!' % resolve_result.coordinates().name())

    def _get_child_solution_coordinates(
        self, db_entry: ICollectionIndex.ICollectionSolution
    ) -> List[ICoordinates]:
        children = []
        for dependency_dict in db_entry.internal()["children"]:
            # get the child entry
            child_solution = (
                self.album.collection_manager()
                .get_collection_index()
                .get_solution_by_collection_id(dependency_dict["collection_id_child"])
            )

            if child_solution is None:
                raise RuntimeError(
                    "Child solution not found in collection index. "
                    "Cannot uninstall parent solution!"
                )

            if child_solution.internal()["installed"]:
                children.append(dict_to_coordinates(child_solution.setup()))
        return children

    def _run_solution_uninstall_routine(
        self, resolve_result: ICollectionSolution
    ) -> None:
        if resolve_result.loaded_solution().setup().uninstall and callable(
            resolve_result.loaded_solution().setup().uninstall
        ):
            self.album.script_manager().run_solution_script(
                resolve_result, ISolution.Action.UNINSTALL
            )
        else:
            module_logger().debug(
                'No "uninstall" routine configured for solution "%s"! Skipping...'
                % resolve_result.loaded_solution().coordinates().name()
            )

    def _run_solution_install_routine(
        self, resolve_result: ICollectionSolution
    ) -> None:
        if resolve_result.loaded_solution().setup().install and callable(
            resolve_result.loaded_solution().setup().install
        ):
            self.album.script_manager().run_solution_script(
                resolve_result, ISolution.Action.INSTALL
            )
        else:
            module_logger().debug(
                'No "install" routine configured for solution "%s". Skipping...'
                % resolve_result.loaded_solution().coordinates().name()
            )

    def _remove_dependencies(
        self,
        solution: ISolution,
        rm_dep: bool = False,
        parent_entry: Optional[ICollectionIndex.ICollectionSolution] = None,
    ) -> None:
        parent = get_parent_dict(solution)
        if parent:
            # recursive call to remove the parent
            resolve_solution = build_resolve_string(parent)
            self.uninstall(resolve_solution, rm_dep)
        elif parent_entry and not solution.setup().dependencies:
            # solution built from its collection entry (its file could not be loaded)
            # carries no "dependencies": take the parent from the collection index
            catalog = self.album.catalogs().get_by_id(
                parent_entry.internal()["catalog_id"]
            )
            resolve_solution = build_resolve_string(
                {
                    "group": parent_entry.setup()["group"],
                    "name": parent_entry.setup()["name"],
                    "version": parent_entry.setup()["version"],
                },
                catalog,
            )
            self.uninstall(resolve_solution, rm_dep)

    def clean_unfinished_installations(self) -> None:
        collection_solution_list = (
            self.album.collection_manager()
            .get_collection_index()
            .get_unfinished_installation_solutions()
        )
        for collection_solution in collection_solution_list:
            catalog = self.album.catalogs().get_by_id(
                collection_solution.internal()["catalog_id"]
            )
            coordinates = dict_to_coordinates(collection_solution.setup())

            # an installation in progress holds the lock of its solution, and the
            # operating system releases it when the album process ends. An unfinished
            # installation whose lock is free was left by a process that ended before
            # finishing it.
            lock = self.album.solutions().get_solution_lock(catalog, coordinates)
            if lock.is_held_by_current_thread() or not lock.acquire(blocking=False):
                module_logger().debug(
                    'Solution "%s" is being installed. Not removing it...' % coordinates
                )
                continue
            try:
                self._clean_unfinished_installation(catalog, coordinates)
            finally:
                lock.release()

    def _remove_failed_installation(self, resolve_result: ICollectionSolution) -> None:
        try:
            self._clean_unfinished_installation(
                resolve_result.catalog(), resolve_result.coordinates()
            )
        except Exception as e:
            # it stays marked unfinished, the next installation removes it
            module_logger().warning(
                'Cannot remove the unfinished installation of "%s": %s'
                % (resolve_result.coordinates(), e)
            )

    def _clean_unfinished_installation(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> None:
        # only called holding the lock of the solution, so no installation of it is in
        # progress. It is looked up again: before the lock was acquired, the installation
        # might have finished, or the solution might have been removed.
        collection_solution = (
            self.album.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(catalog.catalog_id(), coordinates)
        )
        if (
            collection_solution is None
            or not collection_solution.internal()["installation_unfinished"]
        ):
            return

        module_logger().info(
            'Removing the unfinished installation of "%s"...' % coordinates
        )
        path = self.album.solutions().get_solution_file(catalog, coordinates)

        resolve = ResolveResult(
            path=path,
            catalog=catalog,
            collection_entry=collection_solution,
            coordinates=coordinates,
        )

        self.album.solutions().set_cache_paths(
            resolve.loaded_solution(), resolve.catalog()
        )
        # only remove environment when solution has its own environment. The
        # solution is built from its collection entry, which carries no
        # "dependencies", so the parent is taken from the collection index.
        if not collection_solution.internal().get("parent"):
            self._clean_unfinished_installations_environment(resolve)

        self._remove_disc_content_from_solution(resolve)

        if resolve.catalog().is_cache():
            self.album.solutions().remove_solution(resolve.catalog(), coordinates)
        else:
            self.album.solutions().set_uninstalled(resolve.catalog(), coordinates)

    def _clean_unfinished_installations_environment(
        self, resolve: ICollectionSolution
    ) -> None:
        try:
            environment = self.album.environment_manager().set_environment(resolve)
            self.album.environment_manager().remove_environment(environment)
        except LookupError:
            pass

    def _remove_disc_content_from_solution(
        self, resolve_result: ICollectionSolution
    ) -> None:
        remove_link(
            self.album.collection_manager()
            .solutions()
            .get_solution_installation_path(
                resolve_result.catalog(), resolve_result.coordinates()
            )
        )
        remove_link(
            self.album.collection_manager()
            .solutions()
            .get_solution_package_path(
                resolve_result.catalog(), resolve_result.coordinates()
            )
        )
