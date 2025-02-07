from typing import Any, Dict, List, Optional

from album.environments.utils.subcommand import SubProcessError

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.install_manager import IInstallManager
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

        # TODO: run install and download in parallel, enable resource feature
        # self.album.download_manager().download_resources_from_yaml(resolve_result)
        return resolve_result.loaded_solution()

    def _resolve_result_is_installed(self, resolve_result: ICollectionSolution) -> bool:
        if resolve_result.database_entry():  # we know the solution is in the collection
            return (
                self.album.collection_manager()
                .get_collection_index()
                .is_installed(
                    resolve_result.catalog().catalog_id(), resolve_result.coordinates()
                )
            )
        return False

    def _install_loaded_resolve_result(
        self,
        resolve_result: ICollectionSolution,
        parent: bool = False,
        allow_recursive: bool = False,
    ):
        # Load solution
        if not resolve_result.catalog():
            raise RuntimeError(
                "Solution cannot be installed without being associated with a catalog!"
            )
        elif not parent and self._resolve_result_is_installed(resolve_result):
            module_logger().warning(
                'Solution "%s" already installed. Skipping...'
                % resolve_result.loaded_solution().coordinates().name()
            )
            return
        elif parent and self._resolve_result_is_installed(resolve_result):
            return resolve_result  # solution already installed
        else:
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
            # fail when already installed
            if self._resolve_result_is_installed(resolve_result):
                raise RuntimeError(
                    "Solution already installed. Uninstall solution first!"
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

        # run installation recursively
        self._install_active_solution(resolve_result, allow_recursive)

        # mark as installed and remove "installation unfinished"
        self.album.solutions().set_installed(
            resolve_result.catalog(), resolve_result.coordinates()
        )
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
        self, collection_solution: ICollectionSolution, allow_recursive: bool = False
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

        # recursive installation call. Not failing for already installed solutions. parent set to "True"
        self._install_loaded_resolve_result(resolve_result_parent, parent=True)
        return resolve_result_parent

    def uninstall(
        self,
        solution_to_resolve: str,
        rm_dep: bool = False,
        argv: Optional[List[str]] = None,
    ) -> None:
        loaded = False
        try:
            resolve_result = self.album.collection_manager().resolve_installed_and_load(
                solution_to_resolve
            )
            loaded = True
        except ValueError:
            module_logger().info(
                "Cannot load solution. Cannot call uninstall routine. Proceed without..."
            )
            resolve_result = self.album.collection_manager().resolve_installed(
                solution_to_resolve
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

        # get the environment
        environment = None
        try:
            if loaded:
                environment = self.album.environment_manager().set_environment(
                    resolve_result
                )
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
            self._remove_dependencies(resolve_result.loaded_solution(), rm_dep)

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

    def _remove_dependencies(self, solution: ISolution, rm_dep: bool = False) -> None:
        parent = get_parent_dict(solution)
        if parent:
            # recursive call to remove the parent
            resolve_solution = build_resolve_string(parent)
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
            path = self.album.solutions().get_solution_file(
                catalog, dict_to_coordinates(collection_solution.setup())
            )
            coordinates = dict_to_coordinates(collection_solution.setup())

            resolve = ResolveResult(
                path=path,
                catalog=catalog,
                collection_entry=collection_solution,
                coordinates=coordinates,
            )

            self.album.solutions().set_cache_paths(
                resolve.loaded_solution(), resolve.catalog()
            )
            # only remove environment when solution has its own environment
            if not get_parent_dict(resolve.loaded_solution()):
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
