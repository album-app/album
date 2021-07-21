import sys

from album.core.concept.singleton import Singleton
from album.core.controller.resolve_manager import ResolveManager
from album.core.utils.operations.file_operations import copy_folder
from album.core.utils.script import create_script
from album_runner import logging
from album_runner.logging import LogLevel

module_logger = logging.get_active_logger


class InstallManager(metaclass=Singleton):
    """Class handling the installation process of a solution.

    During installation the conda environment (e.g. solutions target environment) the solution is supposed to
    be run in gets created and its dependencies installed. Additionally, the album-runner will be added to the target
    environment. This lightweight program interprets the solution and runs the installation in the target environment.
    After installation the solution is marked as installed in a local catalog.

    Attributes:
        resolve_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.

    """
    # singletons
    resolve_manager = None

    def __init__(self):
        self.resolve_manager = ResolveManager()
        self.configuration = self.resolve_manager.catalog_collection.configuration

    def install(self, path):
        """Function corresponding to the `install` subcommand of `album`."""
        # Load solution
        resolve, active_solution = self.resolve_manager.resolve_and_load(path)

        if not resolve["catalog"]:
            module_logger().debug('album loaded locally: %s...' % str(active_solution))
        else:
            module_logger().debug('album loaded from catalog %s: %s...' % (resolve["catalog"].id, str(active_solution)))

        # execute installation routine
        parent_catalog_id = self._install(active_solution)

        if not resolve["catalog"] or resolve["catalog"].is_local:  # case where a solution file is directly given
            self.add_to_local_catalog(active_solution, resolve["path"].parent)

        self.add_to_solutions_db(resolve["catalog"].id, parent_catalog_id, active_solution)

        module_logger().info('Installed %s!' % active_solution['name'])

        return resolve["catalog"].id

    def add_to_solutions_db(self, catalog_id, parent_catalog_id, active_solution):
        parent_id = None

        if active_solution.parent:
            parent = active_solution.parent

            parent_entry = self.resolve_manager.solution_db.get_solution(
                parent_catalog_id, parent["group"], parent["name"], parent["version"]
            )
            parent_id = parent_entry["solution_id"]

        self.resolve_manager.solution_db.add_solution(
            catalog_id, active_solution["group"], active_solution["name"], active_solution["version"], parent_id
        )

    def add_to_local_catalog(self, active_solution, path):
        """Force adds the installation to the local catalog to be cached for running"""
        self.resolve_manager.catalog_collection.local_catalog.add(active_solution, force_overwrite=True)
        # get the install location
        install_location = self.resolve_manager.catalog_collection.local_catalog.get_solution_path(
            active_solution.group, active_solution.name, active_solution.version
        )

        copy_folder(path, install_location, copy_root_folder=False)
        self.resolve_manager.clean_resolve_tmp()

    def _install(self, active_solution):
        # install environment
        active_solution.environment.install(active_solution.min_album_version)

        # install dependencies first. Recursive call to install with dependencies
        parent_catalog_id = self.install_dependencies(active_solution)

        """Run install routine of album if specified"""
        if active_solution['install'] and callable(active_solution['install']):
            module_logger().debug('Creating install script...')
            script = create_script(active_solution, "\nget_active_solution().install()\n", sys.argv)
            module_logger().debug('Calling install routine specified in solution...')
            logging.configure_logging(active_solution['name'])
            active_solution.environment.run_scripts([script])
            logging.pop_active_logger()
        else:
            module_logger().info(
                'No \"install\" routine configured for solution %s! Will execute nothing! Installation complete!' % active_solution['name']
            )

        return parent_catalog_id

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
        script_path = self.resolve_manager.catalog_collection.resolve_dependency(dependency)["path"]
        # recursive installation call
        catalog_id = self.install(script_path)

        return catalog_id
