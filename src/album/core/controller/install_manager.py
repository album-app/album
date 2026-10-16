from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Set, Tuple

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.install_manager import IInstallManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.controller.environment_manager import EnvironmentManager
from album.core.model.default_values import DefaultValues
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import remove_link
from album.core.utils.operations.resolve_operations import (
    as_tag,
    build_resolve_string,
    check_file_or_url,
    clean_resolve_tmp,
    dict_to_coordinates,
)
from album.core.utils.operations.solution_operations import (
    DEPLOYED_COPIES,
    get_deploy_dict,
    get_parent_dict,
    get_solution_folder,
    version_sort_key,
)
from album.core.utils.operations.url_operations import is_url
from album.environments.utils.file_operations import copy_folder
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
        reinstall: bool = False,
    ) -> ISolution:
        # this needs to happen before any (potentially not completely installed) solution is resolved
        self.clean_unfinished_installations()

        if reinstall:
            # one at a time, see ISolutionHandler.get_upgrade_lock
            with self.album.solutions().get_upgrade_lock():
                return self._reinstall(solution_to_resolve, allow_recursive)

        resolve_result = self.album.collection_manager().resolve_and_load(
            solution_to_resolve
        )
        self._install_loaded_resolve_result(
            resolve_result, parent=False, allow_recursive=allow_recursive
        )

        return resolve_result.loaded_solution()

    def _reinstall(self, solution_to_resolve: str, allow_recursive: bool) -> ISolution:
        """Uninstall a solution and install it again, with the solutions in its environment.

        All that installing them again reads is downloaded or copied first, and the files
        installing them checks are checked, so a failing download or a file outside the
        folder of a solution changes nothing. The solutions running in its environment are
        uninstalled first, deepest first, as a solution others run in cannot be
        uninstalled, and installed again after it, parents first. A solution installed
        from a file, URL or DOI running in its environment prevents the reinstall:
        installing that environment again could break it.

        Plain installations do not take the upgrade lock: an album process installing
        a solution into its environment while the ones there are uninstalled makes
        uninstalling it fail, and those uninstalled before are not installed again.
        """
        try:
            resolve_result = self.album.collection_manager().resolve_installed(
                solution_to_resolve
            )
        except (LookupError, ValueError):
            # not installed: installed as usual
            return self.install(solution_to_resolve, allow_recursive)
        db_entry = resolve_result.database_entry()
        if db_entry is None:  # can only happen if resolve_installed method broken
            raise RuntimeError("Solution not found in collection index!")
        catalog, coordinates = resolve_result.catalog(), resolve_result.coordinates()
        name = f"{catalog.name()}:{coordinates}"

        # the solutions running in its environment, parents first
        children = [
            (
                self.album.catalogs().get_by_id(entry.internal()["catalog_id"]),
                dict_to_coordinates(entry.setup()),
            )
            for entry in reversed(self._installed_children(db_entry))
        ]
        local = [
            str(child) for child_catalog, child in children if child_catalog.is_cache()
        ]
        if local:
            raise RuntimeError(
                'Cannot install "%s" again: "%s", installed from a file, URL or DOI, %s '
                "in its environment."
                % (name, '", "'.join(local), "runs" if len(local) == 1 else "run")
            )
        children_names = [
            f"{child_catalog.name()}:{child}" for child_catalog, child in children
        ]
        if children_names:
            module_logger().info(
                'Installing "%s" again, and the solutions running in its environment: %s'
                % (name, ", ".join(children_names))
            )

        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            # downloaded or copied before anything is uninstalled
            downloads = (
                children if catalog.is_cache() else [(catalog, coordinates)] + children
            )
            try:
                source = name
                if catalog.is_cache():
                    source = self._local_source(
                        solution_to_resolve, catalog, coordinates, tmp_dir
                    )
                for download_catalog, download in downloads:
                    self.album.solutions().retrieve_solution(
                        download_catalog,
                        download,
                        self._staged(tmp_dir, download_catalog, download),
                    )
                # installing them checks their files, once they are uninstalled
                self._check_files_to_install_again(
                    name,
                    (
                        self.album.collection_manager().resolve_and_load(source)
                        if catalog.is_cache()
                        else self._load_staged(tmp_dir, catalog, coordinates)
                    ),
                    [
                        (child_name, self._load_staged(tmp_dir, child_catalog, child))
                        for (child_catalog, child), child_name in zip(
                            children, children_names
                        )
                    ],
                )
            except Exception as e:
                raise RuntimeError(
                    f'Cannot install "{name}" again, nothing was changed: {e}'
                ) from e

            for child_name in reversed(children_names):
                self.uninstall(child_name)
            self.uninstall(name)
            # where installing them reads them from. Installing a solution from a file
            # empties album's tmp folder, tmp_dir with it, so this comes first.
            for download_catalog, download in downloads:
                with self.album.solutions().get_solution_lock(
                    download_catalog, download
                ):
                    copy_folder(
                        self._staged(tmp_dir, download_catalog, download),
                        self.album.solutions().get_solution_package_path(
                            download_catalog, download
                        ),
                        copy_root_folder=False,
                    )

            try:
                loaded_solution = self.install(source, allow_recursive)
            except BaseException:
                if children_names:
                    module_logger().error(
                        'Not installed again, as installing "%s" failed: %s'
                        % (name, ", ".join(children_names))
                    )
                raise

        # one that fails does not keep the others from being installed again
        for child_name in children_names:
            try:
                self.install(child_name, allow_recursive)
            except Exception as e:
                module_logger().error(f'Cannot install "{child_name}" again: {e}')
        not_installed = [
            child_name
            for (child_catalog, child), child_name in zip(children, children_names)
            if not self.album.solutions().is_installed(child_catalog, child)
        ]
        if not_installed:
            raise RuntimeError(
                f'Installed "{name}" again, but not: {", ".join(not_installed)}'
            )
        return loaded_solution

    @staticmethod
    def _staged(tmp_dir: str, catalog: ICatalog, coordinates: ICoordinates) -> Path:
        """Return the folder a solution is downloaded or copied into before a reinstall."""
        return Path(tmp_dir).joinpath(f"{catalog.name()}-{as_tag(coordinates)}")

    def _load_staged(
        self, tmp_dir: str, catalog: ICatalog, coordinates: ICoordinates
    ) -> ICollectionSolution:
        """Load a solution from its copy for a reinstall, installed from it as a folder."""
        path = self._staged(tmp_dir, catalog, coordinates).joinpath(
            DefaultValues.solution_default_name.value
        )
        return ResolveResult(
            path=path,
            catalog=catalog,
            collection_entry=None,
            coordinates=coordinates,
            loaded_solution=self.album.state_manager().load(str(path)),
        )

    def _check_files_to_install_again(
        self,
        name: str,
        solution: ICollectionSolution,
        children: List[Tuple[str, ICollectionSolution]],
    ) -> None:
        """Check the files of a solution and of its children before a reinstall uninstalls them.

        Installing them again checks these files as well, but only once the reinstall has
        uninstalled them. So they are checked here first: if one fails, nothing is
        uninstalled, and the user has to uninstall and install that solution by hand.
        """
        for solution_name, to_install in [(name, solution)] + children:
            try:
                self._check_files(to_install)
            except TypeError as e:
                runs_in = (
                    ""
                    if solution_name == name
                    else f'"{solution_name}", which runs in its environment: '
                )
                raise TypeError(
                    f'{runs_in}{e} Uninstall "{solution_name}" and install it by hand.'
                ) from e

    def _local_source(
        self,
        solution_to_resolve: str,
        catalog: ICatalog,
        coordinates: ICoordinates,
        tmp_dir: str,
    ) -> str:
        """Return what to install a solution from a file, URL or DOI again from.

        Its copy in the collection goes with the installation, so it is copied first.
        """
        if Path(solution_to_resolve).exists():
            # the file, folder or zip given
            return solution_to_resolve
        target = self._staged(tmp_dir, catalog, coordinates)
        if is_url(solution_to_resolve):
            path = check_file_or_url(solution_to_resolve, target)
            if path is None:  # can only happen if check_file_or_url is broken
                raise LookupError(solution_to_resolve)
            # a zip is unpacked into a folder, a single file stays one
            return str(path.parent if path.parent != target else path)
        # given by its coordinates or DOI: the copy in the collection
        copy_folder(
            self.album.solutions().get_solution_package_path(catalog, coordinates),
            target,
            copy_root_folder=False,
        )
        return str(target)

    def _installed_children(
        self, db_entry: ICollectionIndex.ICollectionSolution
    ) -> List[ICollectionIndex.ICollectionSolution]:
        """Return the installed solutions running in its environment, deepest first."""
        index = self.album.collection_manager().get_collection_index()
        children = []
        for link in db_entry.internal()["children"]:
            child = index.get_solution_by_collection_id(link["collection_id_child"])
            if child is not None and child.internal()["installed"]:
                children.extend(self._installed_children(child))
                children.append(child)
        return children

    def upgrade_solutions(
        self, solutions: Optional[List[str]] = None, dry_run: bool = False
    ) -> Dict[str, Any]:
        # one at a time, see ISolutionHandler.get_upgrade_lock
        with self.album.solutions().get_upgrade_lock():
            return self._upgrade_solutions(solutions, dry_run)

    def _upgrade_solutions(
        self, solutions: Optional[List[str]], dry_run: bool
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "dry_run": dry_run,
            "install": [],
            "uninstall": [],
            "keep": [],
            "unused": [],
            "failed": [],
        }
        targets = self._solutions_to_upgrade(solutions)
        catalogs = {
            catalog_id: self.album.catalogs().get_by_id(catalog_id)
            for catalog_id, _, _ in targets
        }
        for catalog in catalogs.values():
            # also refreshes the index of the catalog, which lists its new versions
            self.album.collection_manager().catalogs().update_collection(
                catalog.name(), dry_run=dry_run
            )
            self.album.migration_manager().load_index(catalog, refresh=False)

        to_install = []
        for catalog_id, group, name in sorted(targets):
            catalog = catalogs[catalog_id]
            index = catalog.index()
            if index is None:
                raise RuntimeError("Catalog %s not loaded!" % catalog.name())
            versions = [
                str(solution["version"])
                for solution in index.get_all_solution_versions(group, name)
            ]
            installed = self._installed_versions(catalog_id, group, name)
            if not versions or not installed:
                continue
            latest = max(versions, key=version_sort_key)
            if version_sort_key(latest) > max(map(version_sort_key, installed)):
                to_install.append((catalog_id, group, name, latest))

        scope = set(targets)
        if dry_run:
            result["install"] = [self._as_solution(*key) for key in to_install]
            planned = {key[:3]: key[3] for key in to_install}
        else:
            # installing a new version can install a new version of its parent as well:
            # what this upgrade installed is what is installed afterwards, but not before
            installed_before = self._all_installed()
            for key in to_install:
                solution = self._as_solution(*key)
                try:
                    self.install(solution)
                except Exception as e:
                    module_logger().error(f'Cannot install "{solution}": {e}')
                    result["failed"].append({"solution": solution, "error": str(e)})
            newly_installed = sorted(self._all_installed() - installed_before)
            result["install"] = [self._as_solution(*key) for key in newly_installed]
            # a newer version of a parent, installed with its child, replaces the older
            scope.update(
                key[:3]
                for key in newly_installed
                if not self.album.catalogs().get_by_id(key[0]).is_cache()
            )
            planned = {}

        self._uninstall_replaced_versions(scope, planned, dry_run, result)
        return result

    def _solutions_to_upgrade(
        self, solutions: Optional[List[str]]
    ) -> Set[Tuple[int, str, str]]:
        """Return catalog id, group and name of the installed solutions to upgrade."""
        targets = set()
        if solutions:
            for solution in solutions:
                resolve_result = self.album.collection_manager().resolve_installed(
                    solution
                )
                if resolve_result.catalog().is_cache():
                    module_logger().warning(
                        '"%s" was installed from a file, URL or DOI, not from a catalog.'
                        " Skipping..." % solution
                    )
                    continue
                coordinates = resolve_result.coordinates()
                targets.add(
                    (
                        resolve_result.catalog().catalog_id(),
                        coordinates.group(),
                        coordinates.name(),
                    )
                )
            return targets

        index = self.album.collection_manager().get_collection_index()
        for catalog in self.album.catalogs().get_all():
            if catalog.is_cache():
                continue
            for entry in index.get_all_installed_solutions_by_catalog(
                catalog.catalog_id()
            ):
                targets.add(
                    (
                        catalog.catalog_id(),
                        entry.setup()["group"],
                        entry.setup()["name"],
                    )
                )
        return targets

    def _uninstall_replaced_versions(
        self,
        scope: Set[Tuple[int, str, str]],
        planned: Dict[Tuple[int, str, str], str],
        dry_run: bool,
        result: Dict[str, Any],
    ) -> None:
        """Uninstall each version a newer one replaces, unless solutions run in it.

        The newest installed version of a solution always stays. Without dry_run the
        newer versions are installed already, with dry_run they are in planned.
        """
        replaced: List[
            Tuple[Tuple[int, str, str], str, ICollectionIndex.ICollectionSolution]
        ] = []
        for key in scope:
            versions: Dict[str, Optional[ICollectionIndex.ICollectionSolution]] = dict(
                self._installed_versions(*key)
            )
            if key in planned:
                versions[planned[key]] = None
            replaced.extend(
                (key, version, entry) for version, entry in self._replaced(versions)
            )
        # children first: whether a parent can go depends on the solutions running in it
        replaced.sort(
            key=lambda item: (-self._depth(item[2]), item[0], version_sort_key(item[1]))
        )

        removed: Set[int] = set()
        parents = []
        for key, version, entry in replaced:
            solution = self._as_solution(*key, version)
            used_by = self._runs_in(entry, removed)
            if used_by:
                result["keep"].append({"solution": solution, "used_by": used_by})
                continue
            if not dry_run:
                try:
                    # stays if an album process installed a solution in it meanwhile
                    self._lock_and_uninstall(solution, False, as_dependency=True)
                except Exception as e:
                    # unless another album process uninstalled it meanwhile
                    if version in self._installed_versions(*key):
                        module_logger().error(f'Cannot uninstall "{solution}": {e}')
                        result["failed"].append({"solution": solution, "error": str(e)})
                    continue
                current = self._installed_versions(*key).get(version)
                if current is not None:
                    used_by = self._runs_in(current, removed)
                    result["keep"].append({"solution": solution, "used_by": used_by})
                    continue
            removed.add(entry.internal()["collection_id"])
            result["uninstall"].append(solution)
            if entry.internal()["parent"]:
                parents.append(entry.internal()["parent"])

        # parents no solution runs in anymore stay, the user might run them on their own
        for parent in parents:
            if parent.internal()["collection_id"] in removed:
                continue
            current = (
                self.album.collection_manager()
                .get_collection_index()
                .get_solution_by_collection_id(parent.internal()["collection_id"])
            )
            if current is None or not current.internal()["installed"]:
                continue
            solution = self._as_solution(
                current.internal()["catalog_id"],
                current.setup()["group"],
                current.setup()["name"],
                current.setup()["version"],
            )
            if not self._runs_in(current, removed) and solution not in result["unused"]:
                result["unused"].append(solution)

    @staticmethod
    def _depth(entry: ICollectionIndex.ICollectionSolution) -> int:
        """Return the number of parents above a solution."""
        depth = 0
        parent = entry.internal()["parent"]
        while parent:
            depth += 1
            parent = parent.internal()["parent"]
        return depth

    @staticmethod
    def _replaced(
        versions: Dict[str, Optional[ICollectionIndex.ICollectionSolution]],
    ) -> List[Tuple[str, ICollectionIndex.ICollectionSolution]]:
        """Return the installed versions older than the newest one."""
        if not versions:
            return []
        newest = max(versions, key=version_sort_key)
        return [
            (version, entry)
            for version, entry in versions.items()
            if version != newest and entry is not None
        ]

    def _runs_in(
        self, entry: ICollectionIndex.ICollectionSolution, removed: Set[int]
    ) -> List[str]:
        """Return the installed solutions running in its environment, except removed ones."""
        return [
            self._as_solution(
                child.internal()["catalog_id"],
                child.setup()["group"],
                child.setup()["name"],
                child.setup()["version"],
            )
            for child in self._installed_children(entry)
            if child.internal()["collection_id"] not in removed
        ]

    def _installed_versions(
        self, catalog_id: int, group: str, name: str
    ) -> Dict[str, ICollectionIndex.ICollectionSolution]:
        """Return the installed versions of a solution in a catalog."""
        index = self.album.collection_manager().get_collection_index()
        return {
            entry.setup()["version"]: entry
            for entry in index.get_solutions_by_grp_name(group, name)
            if entry.internal()["catalog_id"] == catalog_id
            and entry.internal()["installed"]
        }

    def _all_installed(self) -> Set[Tuple[int, str, str, str]]:
        """Return catalog id, group, name and version of every installed solution."""
        index = self.album.collection_manager().get_collection_index()
        return {
            (
                catalog.catalog_id(),
                entry.setup()["group"],
                entry.setup()["name"],
                entry.setup()["version"],
            )
            for catalog in self.album.catalogs().get_all()
            for entry in index.get_all_installed_solutions_by_catalog(
                catalog.catalog_id()
            )
        }

    def _as_solution(self, catalog_id: int, group: str, name: str, version: str) -> str:
        catalog_name = self.album.catalogs().get_by_id(catalog_id).name()
        return f"{catalog_name}:{group}:{name}:{version}"

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

        self._check_files(resolve_result)

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

    def _check_files(self, resolve_result: ICollectionSolution) -> None:
        """Check that the environment and the resource file the solution names by path exist.

        Runs before anything is registered or copied; a reinstall runs it before it
        uninstalls anything (see _check_files_to_install_again).
        """
        folder = get_solution_folder(resolve_result)
        # A deployed solution is installed from the copy album deploy wrote next to it, so
        # a file it names by path need not exist here, e.g. an absolute path on the computer
        # it was deployed from. A solution installed from a single file (folder None) has no
        # copies: a relative path asks for its folder, an absolute path has to exist.
        dependencies = [
            dependency
            for dependency, deployed_copy in DEPLOYED_COPIES.items()
            if folder is None or not folder.joinpath(deployed_copy).is_file()
        ]
        self.album.resource_manager().check_file_dependencies(
            resolve_result.loaded_solution(), folder, dependencies
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
        self._lock_and_uninstall(solution_to_resolve, rm_dep, as_dependency=False)

    def _uninstall_parent(self, solution_to_resolve: str, rm_dep: bool) -> None:
        """Uninstall the parent of an uninstalled solution, unless other solutions need it."""
        self._lock_and_uninstall(solution_to_resolve, rm_dep, as_dependency=True)

    def _lock_and_uninstall(
        self, solution_to_resolve: str, rm_dep: bool, as_dependency: bool
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
            self._uninstall(solution_to_resolve, rm_dep, as_dependency)

    def _uninstall(
        self,
        solution_to_resolve: str,
        rm_dep: bool = False,
        as_dependency: bool = False,
    ) -> None:
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
                # the parent of a solution uninstalled with its dependencies stays while
                # other installed solutions run in its environment
                if as_dependency:
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
            self._uninstall_parent(resolve_solution, rm_dep)
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
            self._uninstall_parent(resolve_solution, rm_dep)

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
