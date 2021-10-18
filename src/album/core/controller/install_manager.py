from typing import Optional

from album.core import Solution
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.model.coordinates import Coordinates
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import dict_to_coordinates, solution_to_coordinates, \
    clean_resolve_tmp
from album.core.utils.script import create_solution_script
from album.runner import logging, pop_active_solution

module_logger = logging.get_active_logger


class InstallManager(metaclass=Singleton):
    """Class handling the installation and uninstallation process of a solution.

    Attributes:
        collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    collection_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.configuration = self.collection_manager.configuration

    def install(self, path_or_id, argv=None, cleanup=True) -> ResolveResult:
        """Function corresponding to the `install` subcommand of `album`."""
        # Load solution
        resolve_result = self.collection_manager.resolve_download_and_load(str(path_or_id))
        catalog = resolve_result.catalog

        if not catalog:
            raise RuntimeError("solution cannot be installed without being associated with a catalog")
        else:
            resolve_result.active_solution.set_cache_paths(catalog.name)
            resolve_result.active_solution.set_environment(catalog.name)
            module_logger().debug('solution loaded from catalog \"%s\": %s...' % (catalog.catalog_id, str(
                resolve_result.active_solution)))

        # execute installation routine
        self._install_resolve_result(resolve_result, argv, cleanup)

        return resolve_result

    def install_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, argv=None, cleanup=True) -> ResolveResult:
        catalog = self.collection_manager.catalogs().get_by_name(catalog_name)
        resolve_result = self.collection_manager.resolve_download_and_load_catalog_coordinates(catalog, coordinates)
        self._install_resolve_result(resolve_result, argv, cleanup=cleanup)
        return resolve_result

    def install_from_coordinates(self, coordinates: Coordinates, argv=None, cleanup=True) -> ResolveResult:
        resolve_result = self.collection_manager.resolve_download_and_load_coordinates(coordinates)
        self._install_resolve_result(resolve_result, argv, cleanup=cleanup)
        return resolve_result

    def _install_resolve_result(self, resolve_result, argv, cleanup=True):
        if not resolve_result.active_solution.parent:
            resolve_result.active_solution.set_cache_paths(resolve_result.catalog.name)
            resolve_result.active_solution.set_environment(resolve_result.catalog.name)
        parent_resolve_result = self._install(resolve_result.active_solution, argv)
        if not resolve_result.catalog or resolve_result.catalog.is_cache():  # case where a solution file is directly given
            self.collection_manager.add_solution_to_local_catalog(resolve_result.active_solution,
                                                                  resolve_result.path.parent)
            if cleanup:
                clean_resolve_tmp(self.collection_manager.tmp_cache_dir)
        else:
            parent_catalog_id = None
            if parent_resolve_result:
                parent_catalog_id = parent_resolve_result.catalog.catalog_id
            self.update_in_collection_index(resolve_result.catalog.catalog_id, parent_catalog_id,
                                            resolve_result.active_solution)
        self.collection_manager.solutions().set_installed(resolve_result.catalog, resolve_result.active_solution.coordinates)
        module_logger().info('Installed \"%s\"!' % resolve_result.active_solution['name'])

    def update_in_collection_index(self, catalog_id, parent_catalog_id, active_solution: Solution):
        parent_id = None

        if active_solution.parent:
            parent = active_solution.parent

            parent_entry = self.collection_manager.catalog_collection.get_solution_by_catalog_grp_name_version(
                parent_catalog_id, dict_to_coordinates(parent)
            )
            parent_id = parent_entry["solution_id"]

        #FIXME figure out how to add the parent. can it be in a different catalog? if yes, add catalog and parent_id?!
        self.collection_manager.solutions().update_solution(
            self.collection_manager.catalogs().get_by_id(catalog_id),
            solution_to_coordinates(active_solution),
            active_solution.get_deploy_dict()
        )

    def _install(self, active_solution, argv=None) -> Optional[ResolveResult]:
        # install environment
        if argv is None:
            argv = [""]

        # install dependencies first. Recursive call to install with dependencies
        parent_resolve_result = self.install_dependencies(active_solution)

        if active_solution.parent:
            parent_resolve_result.active_solution.environment.install(parent_resolve_result.active_solution.min_album_version)
            active_solution.environment = parent_resolve_result.active_solution.environment
        else:
            active_solution.environment.install(active_solution.min_album_version)

        """Run install routine of album if specified"""
        if active_solution['install'] and callable(active_solution['install']):
            module_logger().debug('Creating install script...')
            script = create_solution_script(active_solution, "\nget_active_solution().install()\n", argv)
            module_logger().debug('Calling install routine specified in solution...')
            logging.configure_logging(active_solution['name'])
            active_solution.environment.run_scripts([script])
            logging.pop_active_logger()
        else:
            module_logger().info(
                'No \"install\" routine configured for solution \"%s\"! Will execute nothing! Installation complete!' %
                active_solution['name']
            )

        return parent_resolve_result

    # TODO rename install_parent
    def install_dependencies(self, active_solution) -> Optional[ResolveResult]:
        """Handle dependencies in album dependency block"""
        parent_resolve_result = None

        # todo: check if that is necessary any more
        if active_solution.dependencies:
            if 'album' in active_solution.dependencies:
                args = active_solution.dependencies['album']
                for dependency in args:
                    self.install_dependency(dependency)

        if active_solution.parent:
            parent_resolve_result = self.install_dependency(active_solution.parent)

        return parent_resolve_result

    def install_dependency(self, dependency: dict) -> ResolveResult:
        """Calls `install` for a solution declared in a dependency block"""
        resolve = self.collection_manager.resolve_dependency(dependency)
        # recursive installation call
        if resolve.catalog:
            resolve = self.install_from_catalog_coordinates(resolve.catalog.name, resolve.coordinates, cleanup=False)
        else:
            resolve = self.install_from_coordinates(resolve.coordinates, cleanup=False)
        return resolve

    def uninstall(self, path, rm_dep=False):
        """Removes a solution from the disk. Thereby uninstalling its environment and deleting all its downloads.

        Args:
            path:
                The path, DOI or group-name-version information of the solution to remove.
            rm_dep:
                Boolean to indicate whether to remove dependencies too.

        """
        # Todo: some kind of dependency solving in the catalog. Both ways for resolving
        # if c is going to be deleted - check if c is installed
        # if d is going to be deleted - delete c if possible (no other things installed which depend on c)
        #
        # a
        # ├── b
        # │   └── d <- dependency to c
        # └── c <- d depended on c
        # what if solutions depend on solutions from a different catalog?
        # -> ignore this dependency then?

        resolve_result = self.collection_manager.resolve_require_installation_and_load(path)

        if rm_dep:
            self.remove_dependencies(resolve_result.active_solution)

        if not resolve_result.active_solution.parent:
            resolve_result.active_solution.set_environment(resolve_result.catalog.name)
            resolve_result.active_solution.environment.remove()
        resolve_result.active_solution.set_cache_paths(catalog_name=resolve_result.catalog.name)

        self.remove_disc_content(resolve_result.active_solution)

        self.collection_manager.solutions().set_uninstalled(resolve_result.catalog, resolve_result.active_solution.coordinates)

        pop_active_solution()

        module_logger().info("Uninstalled \"%s\"!" % resolve_result.active_solution['name'])

    @staticmethod
    def remove_disc_content(solution):
        force_remove(solution.environment.cache_path)
        force_remove(solution.data_path)
        force_remove(solution.app_path)
        force_remove(solution.package_path)
        force_remove(solution.cache_path)

    def remove_dependencies(self, solution):
        """Recursive call to remove all dependencies"""
        if solution.dependencies:
            if 'album' in solution.dependencies:
                args = solution.dependencies['album']
                for dependency in args:
                    # ToDo: need to search through all installed installations if there is another dependency of what
                    #  we are going to delete... otherwise there will nasty resolving errors during runtime
                    dependency_path = self.collection_manager.resolve_dependency(dependency)["path"]
                    self.uninstall(dependency_path, True)

        if solution.parent:
            parent_path = self.collection_manager.resolve_dependency(solution.parent)["path"]
            self.uninstall(parent_path, True)