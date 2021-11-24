from typing import Optional

from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.environment_manager import EnvironmentManager
from album.core.model.catalog import Catalog
from album.core.model.configuration import Configuration
from album.core.model.environment import Environment
from album.core.model.resolve_result import ResolveResult
from album.runner.model.solution import Solution
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import clean_resolve_tmp, build_resolve_string, dict_to_coordinates
from album.core.utils.operations.resolve_operations import clean_resolve_tmp, build_resolve_string, dict_to_coordinates
from album.core.utils.operations.solution_operations import get_deploy_dict, get_parent_dict, set_cache_paths, \
    remove_disc_content_from_solution
from album.runner import album_logging
from album.runner.concept.script_creator import ScriptCreatorInstall, ScriptCreatorUnInstall
from album.runner.model.coordinates import Coordinates
from album.runner.model.solution import Solution

module_logger = album_logging.get_active_logger


class InstallManager(metaclass=Singleton):
    """Class handling the installation and uninstallation process of a solution.

    Attributes:
        collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.
        environment_manager:
            Manages the environments.
        configuration:
            The configuration of the album instance.

    """
    # singletons
    collection_manager = None
    environment_manager = None
    configuration = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.configuration = Configuration()
        self.environment_manager = EnvironmentManager()

    def install(self, resolve_solution, argv=None):
        """Function corresponding to the `install` subcommand of `album`."""
        self._install(resolve_solution, argv, parent=False)

    def _install(self, resolve_solution, argv=None, parent=False) -> ResolveResult:
        """Internal installation entry point for `install` subcommand of `album`."""
        # Load solution
        resolve_result = self.collection_manager.resolve_download_and_load(str(resolve_solution))

        if not resolve_result.catalog:
            raise RuntimeError("Solution cannot be installed without being associated with a catalog!")
        elif not parent and self._resolve_result_is_installed(resolve_result):
            raise RuntimeError("Solution already installed. Uninstall solution first!")
        elif parent and self._resolve_result_is_installed(resolve_result):
            return resolve_result  # solution already installed
        else:
            module_logger().debug(
                'solution loaded from catalog \"%s\": %s...' % (
                    resolve_result.catalog.catalog_id, str(resolve_result.loaded_solution)
                )
            )

        # execute installation routine
        self._install_resolve_result(resolve_result, argv, parent)

        return resolve_result

    def install_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, argv=None) -> ResolveResult:
        """API entry point for installation from a specific catalog"""
        return self._install_from_catalog_coordinates(catalog_name, coordinates, argv, parent=False)

    def _install_from_catalog_coordinates(self, catalog_name: str, coordinates: Coordinates, argv=None,
                                          parent=False) -> ResolveResult:
        """Internal entry point for installation from a specific catalog"""
        catalog = self.collection_manager.catalogs().get_by_name(catalog_name)
        resolve_result = self.collection_manager.resolve_download_and_load_catalog_coordinates(catalog, coordinates)
        self._install_resolve_result(resolve_result, argv, parent=parent)
        return resolve_result

    def install_from_coordinates(self, coordinates: Coordinates, argv=None) -> ResolveResult:
        """API entry point for installation from any catalog"""
        return self._install_from_coordinates(coordinates, argv, parent=False)

    def _install_from_coordinates(self, coordinates: Coordinates, argv=None, parent=False) -> ResolveResult:
        """Internal entry point for installation from any catalog"""
        resolve_result = self.collection_manager.resolve_download_and_load_coordinates(coordinates)
        self._install_resolve_result(resolve_result, argv, parent=parent)
        return resolve_result

    def _resolve_result_is_installed(self, resolve_result: ResolveResult) -> bool:
        """Checks whether a resolve_result is already installed."""
        if resolve_result.collection_entry:  # we know the solution is in the collection
            return self.collection_manager.catalog_collection.is_installed(
                resolve_result.catalog.catalog_id,
                resolve_result.coordinates
            )
        return False

    def _install_resolve_result(self, resolve_result: ResolveResult, argv, parent=False):
        """Installs a resolve result.

        CAUTION: Solution must be loaded!
        """
        module_logger().info('Installing \"%s\"..' % resolve_result.loaded_solution.coordinates.name)
        if not parent:  # fail when already installed
            if self._resolve_result_is_installed(resolve_result):
                raise RuntimeError("Solution already installed. Uninstall solution first!")

        self.clean_unfinished_installations()

        self._register(resolve_result, parent)

        # mark as installation unfinished
        self.collection_manager.solutions().set_installation_unfinished(
            resolve_result.catalog, resolve_result.loaded_solution.coordinates
        )

        # run installation recursively
        parent_resolve_result = self._install_active_solution(
            resolve_result.loaded_solution, resolve_result.catalog, argv
        )

        if parent_resolve_result:
            self.set_parent(parent_resolve_result, resolve_result)

        # mark as installed
        self.collection_manager.solutions().set_installed(
            resolve_result.catalog, resolve_result.loaded_solution.coordinates
        )
        module_logger().info(
            'Installed \"%s\"! execute with `album run %s`' % (
                resolve_result.loaded_solution.coordinates.name,
                str(resolve_result.coordinates)
            )
        )

    def _register(self, resolve_result: ResolveResult, parent=False):
        """Registers a resolve result in the collection"""
        # register in collection
        if resolve_result.catalog.is_cache():
            # a cache catalog is living in the collection so no need to update, we can add it directly
            self.collection_manager.add_solution_to_local_catalog(
                resolve_result.loaded_solution,
                resolve_result.path.parent  # the directory holding the solution file
            )
            if not parent:
                clean_resolve_tmp(self.configuration.cache_path_tmp_user)
        else:
            # update the collection holding the solution entry
            self.update_in_collection_index(resolve_result)

    def set_parent(self, parent_resolve_result: ResolveResult, resolve_result: ResolveResult):
        """Sets the parent of a solution"""
        self.collection_manager.solutions().set_parent(
            parent_resolve_result.catalog,
            resolve_result.catalog,
            parent_resolve_result.coordinates,
            resolve_result.coordinates
        )

    def update_in_collection_index(self, resolve_result: ResolveResult):
        """Updates the collection entry of the resolved solution"""
        # update the solution in the collection
        self.collection_manager.solutions().update_solution(
            resolve_result.catalog,
            resolve_result.coordinates,
            get_deploy_dict(resolve_result.loaded_solution)
        )

    def _install_active_solution(
            self, active_solution: Solution, catalog: Catalog, argv=None
    ) -> Optional[ResolveResult]:
        """Installation routine for a loaded solution."""
        # install environment
        if argv is None:
            argv = [""]

        parent_resolve_result = None

        parent = get_parent_dict(active_solution)
        if parent:
            # install dependencies first. Recursive call to install with dependencies
            parent_resolve_result = self._install_parent(parent)

            # resolve environment - at this point all parents should be already installed
            environment = self.environment_manager.set_environment(active_solution, catalog)
        else:
            environment = self.environment_manager.install_environment(active_solution, catalog)

        self.run_solution_install_routine(active_solution, environment, argv)

        return parent_resolve_result

    def run_solution_install_routine(self, active_solution: Solution, environment: Environment, argv):
        """Run install routine of album if specified"""
        script_creator_install = ScriptCreatorInstall()

        if active_solution.setup.install and callable(active_solution.setup.install):
            module_logger().debug('Creating install script...')
            script = script_creator_install.create_script(active_solution, argv)
            module_logger().debug('Calling install routine specified in solution...')
            album_logging.configure_logging(active_solution.coordinates.name)
            self.environment_manager.run_scripts(environment, [script])
            album_logging.pop_active_logger()
        else:
            module_logger().debug(
                'No \"install\" routine configured for solution \"%s\". Skipping...' %
                active_solution.coordinates.name
            )

    def _install_parent(self, parent_dict: dict) -> ResolveResult:
        """Installs a parent of a solution given its description as a dictionary."""
        resolve_solution = build_resolve_string(parent_dict)

        # recursive installation call. Not failing for already installed solutions. parent set to "True"
        return self._install(resolve_solution, parent=True)

    def uninstall(self, resolve_solution, rm_dep=False, argv=None):
        """Removes a solution from the disk. Thereby uninstalling its environment and deleting all its downloads.

        Args:
            argv:
                Arguments which should be appended to the script call
            resolve_solution:
                The path, DOI or group-name-version information of the solution to remove.
            rm_dep:
                Boolean to indicate whether to remove parents too.

        """
        self._uninstall(resolve_solution, rm_dep, parent=False, argv=argv)

    def _uninstall(self, resolve_solution, rm_dep=False, argv=None, parent=False):
        """Internal installation entry point for `uninstall` subcommand of `album`."""
        resolve_result = self.collection_manager.resolve_require_installation_and_load(resolve_solution)
        module_logger().info("Uninstalling \"%s\".." % resolve_result.loaded_solution.coordinates.name)

        # get the environment
        environment = self.environment_manager.set_environment(resolve_result.loaded_solution, resolve_result.catalog)

        self.run_solution_uninstall_routine(resolve_result.loaded_solution, environment, argv)

        parent = resolve_result.collection_entry.internal["parent"]
        if not parent:
            self.environment_manager.remove_environment(environment)

        if resolve_result.collection_entry.internal["children"]:
            children = []
            for dependency_dict in resolve_result.collection_entry.internal["children"]:
                # get the child entry
                child_solution = self.collection_manager.catalog_collection.get_solution_by_collection_id(dependency_dict["collection_id_child"])
                if child_solution.internal['installed']:
                    children.append(str(dict_to_coordinates(child_solution.setup)))

            if children:

                module_logger().info("The following solutions depend on this installation: %s. Not uninstalling %s..."
                                     % (", ".join(children), str(resolve_result.coordinates)))
                if parent:
                    return

                raise RuntimeError(
                    "Cannot uninstall \"%s\". Other solution depend on this installation! Inspect log for more information!"
                    % resolve_result.coordinates
                )

        remove_disc_content_from_solution(resolve_result.loaded_solution)
        self.environment_manager.remove_disc_content_from_environment(environment)
        self.collection_manager.solutions().set_uninstalled(resolve_result.catalog,
                                                            resolve_result.loaded_solution.coordinates)

        if rm_dep:  # remove dependencies (parent of the solution) last
            self.remove_dependencies(resolve_result.loaded_solution, rm_dep)

        module_logger().info("Uninstalled \"%s\"!" % resolve_result.loaded_solution.coordinates.name)

    def run_solution_uninstall_routine(self, active_solution: Solution, environment: Environment, argv):
        """Run uninstall routine of album if specified. Expects environment to be set!"""
        script_creator_un_install = ScriptCreatorUnInstall()

        if active_solution.setup.uninstall and callable(active_solution.setup.uninstall):
            module_logger().debug('Creating uninstall script...')
            script = script_creator_un_install.create_script(active_solution, argv)
            module_logger().debug('Calling uninstall routine specified in solution...')
            album_logging.configure_logging(active_solution.coordinates.name)
            self.environment_manager.run_scripts(environment, [script])
            album_logging.pop_active_logger()
        else:
            module_logger().info(
                'No \"uninstall\" routine configured for solution \"%s\"! Skipping...' %
                active_solution.coordinates.name
            )

    def remove_dependencies(self, solution: Solution, rm_dep=False):
        parent = get_parent_dict(solution)
        if parent:
            # recursive call to remove the parent
            resolve_solution = build_resolve_string(parent)
            self._uninstall(resolve_solution, rm_dep, parent=True)

    def clean_unfinished_installations(self):
        solution_list = self.collection_manager.catalog_collection.get_unfinished_installation_solutions()
        for solution_entry in solution_list:
            catalog = self.collection_manager.catalog_handler.get_by_id(solution_entry["catalog_id"])
            path = catalog.get_solution_file(dict_to_coordinates(solution_entry))

            resolve = ResolveResult(
                path=path,
                catalog=catalog,
                collection_entry=solution_entry,
                coordinates=dict_to_coordinates(solution_entry)
            )
            self.collection_manager.retrieve_and_load_resolve_result(resolve)

            set_cache_paths(resolve.loaded_solution, resolve.catalog)

            # only remove environment when it has its own environment
            if not get_parent_dict(resolve.loaded_solution):
                environment = self.environment_manager.set_environment(resolve.loaded_solution, resolve.catalog)
                self.environment_manager.remove_environment(environment)

            remove_disc_content_from_solution(resolve.loaded_solution)

            self.collection_manager.solutions().set_uninstalled(resolve.catalog, resolve.loaded_solution.coordinates)
