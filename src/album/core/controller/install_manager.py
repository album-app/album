from typing import Optional

from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.conda_manager import CondaManager
from album.core.model.configuration import Configuration
from album.core.model.coordinates import Coordinates
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import clean_resolve_tmp, build_resolve_string
from album.core.utils.script import create_solution_script
from album.runner import logging

module_logger = logging.get_active_logger


class InstallManager(metaclass=Singleton):
    """Class handling the installation and uninstallation process of a solution.

    Attributes:
        collection_manager:
            Holding all configured catalogs. Resolves inside our outside catalogs.
        conda_manager:
            Managing conda environments.
        configuration:
            The configuration of the album instance.

    """
    # singletons
    collection_manager = None
    conda_manager = None
    configuration = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self.conda_manager = CondaManager()
        self.configuration = Configuration()

    def install(self, resolve_solution, argv=None):
        """Function corresponding to the `install` subcommand of `album`."""
        self._install(resolve_solution, argv, parent=False)

    def _install(self, resolve_solution, argv=None, parent=False) -> ResolveResult:
        """Internal installation entry point for `install` subcommand of `album`."""
        # Load solution
        resolve_result = self.collection_manager.resolve_download_and_load(str(resolve_solution))
        catalog = resolve_result.catalog

        if not catalog:
            raise RuntimeError("Solution cannot be installed without being associated with a catalog!")
        elif not parent and self._resolve_result_is_installed(resolve_result):
            raise RuntimeError("Solution already installed. Uninstall solution first!")
        else:
            resolve_result.loaded_solution.set_cache_paths(catalog.name)
            module_logger().debug(
                'solution loaded from catalog \"%s\": %s...' % (catalog.catalog_id, str(resolve_result.loaded_solution))
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
        module_logger().info('Installing \"%s\"..' % resolve_result.loaded_solution['name'])
        if not parent:  # fail when already installed
            if self._resolve_result_is_installed(resolve_result):
                raise RuntimeError("Solution already installed. Uninstall solution first!")

        if not resolve_result.loaded_solution.parent:
            resolve_result.loaded_solution.set_cache_paths(resolve_result.catalog.name)
            resolve_result.loaded_solution.set_environment(resolve_result.catalog.name)

        parent_resolve_result = self._install_active_solution(resolve_result.loaded_solution, argv)

        if resolve_result.catalog.is_cache():
            # a cache catalog is living in the collection so no need to update
            self.collection_manager.add_solution_to_local_catalog(
                resolve_result.loaded_solution,
                resolve_result.path.parent  # the directory holding the solution file
            )
            if not parent:
                clean_resolve_tmp(self.configuration.cache_path_tmp)
        else:
            # update the collection holding the solution entry
            self.update_in_collection_index(resolve_result)

        if parent_resolve_result:
            self.set_parent(parent_resolve_result, resolve_result)

        # mark as installed
        self.collection_manager.solutions().set_installed(
            resolve_result.catalog, resolve_result.loaded_solution.coordinates
        )
        module_logger().info('Installed \"%s\"!' % resolve_result.loaded_solution['name'])

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
            resolve_result.loaded_solution.get_deploy_dict()
        )

    def _install_active_solution(self, active_solution, argv=None) -> Optional[ResolveResult]:
        """Installation routine for a loaded solution."""
        # install environment
        if argv is None:
            argv = [""]

        parent_resolve_result = None

        if active_solution.parent:
            # install dependencies first. Recursive call to install with dependencies
            parent_resolve_result = self._install_parent(active_solution.parent)

            active_solution.environment = parent_resolve_result.loaded_solution.environment
        else:
            self.conda_manager.install(active_solution.environment, active_solution.min_album_version)

        self.run_solution_install_routine(active_solution, argv)

        return parent_resolve_result

    def run_solution_install_routine(self, active_solution, argv):
        """Run install routine of album if specified"""
        if active_solution['install'] and callable(active_solution['install']):
            module_logger().debug('Creating install script...')
            script = create_solution_script(active_solution, "\nget_active_solution().install()\n", argv)
            module_logger().debug('Calling install routine specified in solution...')
            logging.configure_logging(active_solution['name'])
            self.conda_manager.run_scripts(active_solution.environment, [script])
            logging.pop_active_logger()
        else:
            module_logger().debug(
                'No \"install\" routine configured for solution \"%s\". Skipping.' %
                active_solution['name']
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
        module_logger().info("Uninstalling \"%s\".." % resolve_result.loaded_solution['name'])

        # set the environment
        if not resolve_result.loaded_solution.parent:
            resolve_result.loaded_solution.set_environment(resolve_result.catalog.name)
            self.conda_manager.set_environment_path(resolve_result.loaded_solution.environment)
        else:
            # resolve the parent
            resolve_result_parent = self.collection_manager.resolve_require_installation_and_load(
                build_resolve_string(resolve_result.loaded_solution.parent)
            )
            resolve_result.loaded_solution.set_environment(resolve_result_parent.catalog.name)
            self.conda_manager.set_environment_path(resolve_result.loaded_solution.environment)

        self.run_solution_uninstall_routine(resolve_result.loaded_solution, argv)

        if not resolve_result.loaded_solution.parent:
            self.conda_manager.remove_environment(resolve_result.loaded_solution.environment.name)

        if resolve_result.collection_entry["children"]:
            children = []
            for dependency_dict in resolve_result.collection_entry["children"]:
                # get the child entry
                child_entry = self.collection_manager.catalog_collection.get_solution(
                    dependency_dict["collection_id_child"]
                )
                # get the child catalog
                child_catalog = self.collection_manager.catalogs().get_by_id(dependency_dict["catalog_id_child"])

                children.append(build_resolve_string(child_entry, child_catalog))

            module_logger().info(
                "The following solutions depend on this installation: %s. Aborting..." % ", ".join(children)
            )
            if parent:
                return

            raise RuntimeError(
                "Cannot uninstall \"%s\". Other solution depend on this installation! Inspect log for more information!"
                % resolve_result.collection_entry["name"]
            )

        resolve_result.loaded_solution.set_cache_paths(catalog_name=resolve_result.catalog.name)

        self.remove_disc_content(resolve_result.loaded_solution)

        self.collection_manager.solutions().set_uninstalled(resolve_result.catalog,
                                                            resolve_result.loaded_solution.coordinates)

        if rm_dep:  # remove dependencies (parent of the solution) last
            self.remove_dependencies(resolve_result.loaded_solution, rm_dep)

        module_logger().info("Uninstalled \"%s\"!" % resolve_result.loaded_solution['name'])

    def run_solution_uninstall_routine(self, active_solution, argv):
        """Run uninstall routine of album if specified"""
        if active_solution['uninstall'] and callable(active_solution['uninstall']):
            module_logger().debug('Creating uninstall script...')
            script = create_solution_script(active_solution, "\nget_active_solution().uninstall()\n", argv)
            module_logger().debug('Calling uninstall routine specified in solution...')
            logging.configure_logging(active_solution['name'])
            self.conda_manager.run_scripts(active_solution.environment, [script])
            logging.pop_active_logger()
        else:
            module_logger().info(
                'No \"uninstall\" routine configured for solution \"%s\"! Will execute nothing!' %
                active_solution['name']
            )

    def remove_dependencies(self, solution, rm_dep=False):
        if solution.parent:
            # recursive call to remove the parent
            resolve_solution = build_resolve_string(solution.parent)
            self._uninstall(resolve_solution, rm_dep, parent=True)

    @staticmethod
    def remove_disc_content(solution):
        force_remove(solution.environment.cache_path)
        force_remove(solution.data_path)
        force_remove(solution.app_path)
        force_remove(solution.package_path)
        force_remove(solution.cache_path)
