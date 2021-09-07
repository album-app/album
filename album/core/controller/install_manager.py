import sys

from album.core import AlbumClass
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import dict_to_group_name_version, solution_to_group_name_version
from album.core.utils.script import create_solution_script
from album_runner import logging, pop_active_solution

module_logger = logging.get_active_logger


class InstallManager(metaclass=Singleton):
    """Class handling the installation and uninstallation process of a solution.

    During installation the conda environment (e.g. solutions target environment) the solution is supposed to
    be run in gets created and its dependencies installed. Additionally, the album-runner will be added to the target
    environment. This lightweight program interprets the solution and runs the installation in the target environment.
    After installation the solution is marked as installed in a local catalog.

    When solutions are not required any more they can be deinstalled, either with their dependencies or without.
    During removal of a solution its environment will be removed and all additional downloads are removed from the disk.

    Attributes:
        collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    collection_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.configuration = self.collection_manager.configuration

    def install(self, path):
        """Function corresponding to the `install` subcommand of `album`."""
        # Load solution
        resolve_result = self.collection_manager.resolve_download_and_load(path)
        solution = resolve_result.active_solution
        catalog = resolve_result.catalog

        if not catalog:
            module_logger().debug('solution loaded locally: %s...' % str(solution))
        else:
            module_logger().debug('solution loaded from catalog %s: %s...' % (catalog.catalog_id, str(
                solution)))

        # execute installation routine
        parent_catalog_id = self._install(solution)

        if not catalog or catalog.is_cache():  # case where a solution file is directly given
            self.collection_manager.add_solution_to_local_catalog(solution, resolve_result.path.parent)
        else:
            self.update_in_collection_index(catalog.catalog_id, parent_catalog_id, solution)

        self.collection_manager.solutions().set_installed(catalog, solution)
        module_logger().info('Installed %s!' % solution['name'])

        return catalog.catalog_id

    def update_in_collection_index(self, catalog_id, parent_catalog_id, active_solution: AlbumClass):
        parent_id = None

        if active_solution.parent:
            parent = active_solution.parent

            parent_entry = self.collection_manager.catalog_collection.get_solution_by_catalog_grp_name_version(
                parent_catalog_id, dict_to_group_name_version(parent)
            )
            parent_id = parent_entry["solution_id"]

        #FIXME figure out how to add the parent. can it be in a different catalog? if yes, add catalog and parent_id?!
        self.collection_manager.solutions().update_solution(
            self.collection_manager.catalogs().get_by_id(catalog_id),
            solution_to_group_name_version(active_solution),
            active_solution.get_deploy_dict()
        )

    def _install(self, active_solution):
        # install environment
        active_solution.environment.install(active_solution.min_album_version)

        # install dependencies first. Recursive call to install with dependencies
        parent_catalog_id = self.install_dependencies(active_solution)

        """Run install routine of album if specified"""
        if active_solution['install'] and callable(active_solution['install']):
            module_logger().debug('Creating install script...')
            script = create_solution_script(active_solution, "\nget_active_solution().install()\n", sys.argv)
            module_logger().debug('Calling install routine specified in solution...')
            logging.configure_logging(active_solution['name'])
            active_solution.environment.run_scripts([script])
            logging.pop_active_logger()
        else:
            module_logger().info(
                'No \"install\" routine configured for solution %s! Will execute nothing! Installation complete!' %
                active_solution['name']
            )

        return parent_catalog_id

    # TODO rename install_parent
    def install_dependencies(self, active_solution):
        """Handle dependencies in album dependency block"""
        parent_catalog_id = None

        # todo: check if that is necessary any more
        if active_solution.dependencies:
            if 'album' in active_solution.dependencies:
                args = active_solution.dependencies['album']
                for dependency in args:
                    self.install_dependency(dependency)

        if active_solution.parent:
            parent_catalog_id = self.install_dependency(active_solution.parent)

        return parent_catalog_id

    def install_dependency(self, dependency):
        """Calls `install` for a solution declared in a dependency block"""
        script_path = self.collection_manager.resolve_dependency(dependency).path
        # recursive installation call
        catalog_id = self.install(script_path)

        return catalog_id

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

        resolve_result.active_solution.environment.remove()

        self.remove_disc_content(resolve_result.active_solution)

        self.collection_manager.solutions().set_uninstalled(resolve_result.catalog, resolve_result.active_solution)

        pop_active_solution()

        module_logger().info("Uninstalled %s!" % resolve_result.active_solution['name'])

    @staticmethod
    def remove_disc_content(solution):
        force_remove(solution.environment.cache_path)
        force_remove(solution.cache_path_download)
        force_remove(solution.cache_path_app)
        force_remove(solution.cache_path_solution)

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
