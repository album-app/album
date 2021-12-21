from typing import Optional

from album.core.api.album import IAlbum
from album.core.api.controller.install_manager import IInstallManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.environment import IEnvironment
from album.core.api.model.resolve_result import IResolveResult
from album.core.controller.environment_manager import EnvironmentManager
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import clean_resolve_tmp, build_resolve_string, dict_to_coordinates
from album.core.utils.operations.solution_operations import get_deploy_dict, get_parent_dict
from album.core.utils.operations.solution_operations import remove_disc_content_from_solution
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import ScriptCreatorInstall, ScriptCreatorUnInstall

module_logger = album_logging.get_active_logger


class InstallManager(IInstallManager):

    def __init__(self, album: IAlbum):
        self.album = album

    def install(self, resolve_solution, argv=None):
        self._install(resolve_solution, argv, parent=False)

    def _install(self, resolve_solution, argv=None, parent=False) -> IResolveResult:
        """Internal installation entry point for `install` subcommand of `album`."""
        # Load solution
        resolve_result = self.album.collection_manager().resolve_download_and_load(str(resolve_solution))

        if not resolve_result.catalog():
            raise RuntimeError("Solution cannot be installed without being associated with a catalog!")
        elif not parent and self._resolve_result_is_installed(resolve_result):
            raise RuntimeError("Solution already installed. Uninstall solution first!")
        elif parent and self._resolve_result_is_installed(resolve_result):
            return resolve_result  # solution already installed
        else:
            module_logger().debug(
                'solution loaded from catalog \"%s\": %s...' % (
                    resolve_result.catalog().catalog_id(), str(resolve_result.loaded_solution())
                )
            )

        # execute installation routine
        self._install_resolve_result(resolve_result, argv, parent)

        return resolve_result

    def install_from_catalog_coordinates(self, catalog_name: str, coordinates: ICoordinates,
                                         argv=None) -> IResolveResult:
        return self._install_from_catalog_coordinates(catalog_name, coordinates, argv, parent=False)

    def _install_from_catalog_coordinates(self, catalog_name: str, coordinates: ICoordinates, argv=None,
                                          parent=False) -> IResolveResult:
        """Internal entry point for installation from a specific catalog"""
        catalog = self.album.collection_manager().catalogs().get_by_name(catalog_name)
        resolve_result = self.album.collection_manager().resolve_download_and_load_catalog_coordinates(catalog,
                                                                                                       coordinates)
        self._install_resolve_result(resolve_result, argv, parent=parent)
        return resolve_result

    def install_from_coordinates(self, coordinates: ICoordinates, argv=None) -> IResolveResult:
        return self._install_from_coordinates(coordinates, argv, parent=False)

    def _install_from_coordinates(self, coordinates: ICoordinates, argv=None, parent=False) -> IResolveResult:
        """Internal entry point for installation from any catalog"""
        resolve_result = self.album.collection_manager().resolve_download_and_load_coordinates(coordinates)
        self._install_resolve_result(resolve_result, argv, parent=parent)
        return resolve_result

    def _resolve_result_is_installed(self, resolve_result: IResolveResult) -> bool:
        """Checks whether a resolve_result is already installed."""
        if resolve_result.collection_entry():  # we know the solution is in the collection
            return self.album.collection_manager().get_collection_index().is_installed(
                resolve_result.catalog().catalog_id(),
                resolve_result.coordinates()
            )
        return False

    def _install_resolve_result(self, resolve_result: IResolveResult, argv, parent=False):
        """Installs a resolve result.

        CAUTION: Solution must be loaded!
        """
        module_logger().info('Installing \"%s\"...' % resolve_result.loaded_solution().coordinates().name())
        if not parent:  # fail when already installed
            if self._resolve_result_is_installed(resolve_result):
                raise RuntimeError("Solution already installed. Uninstall solution first!")

        if not parent:
            self.clean_unfinished_installations()

        self._register(resolve_result)

        if not parent:
            if resolve_result.catalog().is_cache():
                # always clean after registration to a catalog!
                clean_resolve_tmp(self.album.configuration().cache_path_tmp_user())

        # mark as "installation unfinished"
        self.album.collection_manager().solutions().set_installation_unfinished(
            resolve_result.catalog(), resolve_result.loaded_solution().coordinates()
        )

        # run installation recursively
        parent_resolve_result = self._install_active_solution(
            resolve_result.loaded_solution(), resolve_result.catalog(), argv
        )

        if parent_resolve_result:
            self._set_parent(parent_resolve_result, resolve_result)
        else:
            self._remove_parent(resolve_result)

        # mark as installed and remove "installation unfinished"
        self.album.collection_manager().solutions().set_installed(
            resolve_result.catalog(), resolve_result.loaded_solution().coordinates()
        )
        module_logger().info(
            'Installed \"%s\"! execute with `album run %s`' % (
                resolve_result.loaded_solution().coordinates().name(),
                str(resolve_result.coordinates())
            )
        )

    def _register(self, resolve_result: IResolveResult):
        """Registers a resolve result in the collection"""
        # register in collection
        if resolve_result.catalog().is_cache():
            # a cache catalog is living in the collection so no need to update, we can add it directly
            self.album.collection_manager().add_solution_to_local_catalog(
                resolve_result.loaded_solution(),
                resolve_result.path().parent  # the directory holding the solution file
            )
        else:
            # update the collection holding the solution entry
            self._update_in_collection_index(resolve_result)

    def _set_parent(self, parent_resolve_result: IResolveResult, resolve_result: IResolveResult):
        """Sets the parent of a solution"""
        self.album.collection_manager().solutions().set_parent(
            parent_resolve_result.catalog(),
            resolve_result.catalog(),
            parent_resolve_result.coordinates(),
            resolve_result.coordinates()
        )

    def _remove_parent(self, resolve_result: IResolveResult):
        """Sets the parent of a solution"""
        self.album.collection_manager().solutions().remove_parent(
            resolve_result.catalog(),
            resolve_result.coordinates()
        )

    def _update_in_collection_index(self, resolve_result: IResolveResult):
        """Updates the collection entry of the resolved solution"""
        # update the solution in the collection
        self.album.collection_manager().solutions().update_solution(
            resolve_result.catalog(),
            resolve_result.coordinates(),
            get_deploy_dict(resolve_result.loaded_solution())
        )

    def _install_active_solution(
            self, active_solution: ISolution, catalog: ICatalog, argv=None
    ) -> Optional[IResolveResult]:
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
            environment = self.album.environment_manager().set_environment(active_solution, catalog)
        else:
            environment = self.album.environment_manager().install_environment(active_solution, catalog)

        self._run_solution_install_routine(active_solution, environment, argv)

        return parent_resolve_result

    def _run_solution_install_routine(self, active_solution: ISolution, environment: IEnvironment, argv):
        """Run install routine of album if specified"""
        script_creator_install = ScriptCreatorInstall()

        if active_solution.setup().install and callable(active_solution.setup().install):
            module_logger().debug('Creating install script...')
            script = script_creator_install.create_script(active_solution, argv)
            module_logger().debug('Calling install routine specified in solution...')
            album_logging.configure_logging(active_solution.coordinates().name())
            self.album.environment_manager().run_scripts(environment, [script])
            album_logging.pop_active_logger()
        else:
            module_logger().debug(
                'No \"install\" routine configured for solution \"%s\". Skipping...' %
                active_solution.coordinates().name()
            )

    def _install_parent(self, parent_dict: dict) -> IResolveResult:
        """Installs a parent of a solution given its description as a dictionary."""
        resolve_solution = build_resolve_string(parent_dict)

        # recursive installation call. Not failing for already installed solutions. parent set to "True"
        return self._install(resolve_solution, parent=True)

    def uninstall(self, resolve_solution, rm_dep=False, argv=None):
        self._uninstall(resolve_solution, rm_dep, argv=argv)

    def _uninstall(self, resolve_solution, rm_dep=False, argv=None):
        """Internal installation entry point for `uninstall` subcommand of `album`."""
        resolve_result = self.album.collection_manager().resolve_require_installation_and_load(resolve_solution)
        module_logger().info("Uninstalling \"%s\"..." % resolve_result.loaded_solution().coordinates().name())

        # get the environment
        environment = self.album.environment_manager().set_environment_from_database(
            resolve_result.loaded_solution(),
            resolve_result.collection_entry(),
            resolve_result.catalog()
        )

        self._run_solution_uninstall_routine(resolve_result.loaded_solution(), environment, argv)

        parent = resolve_result.collection_entry().internal()["parent"]
        if not parent:
            self.album.environment_manager().remove_environment(environment)

        if resolve_result.collection_entry().internal()["children"]:
            children = []
            for dependency_dict in resolve_result.collection_entry().internal()["children"]:
                # get the child entry
                child_solution = self.album.collection_manager().get_collection_index().get_solution_by_collection_id(
                    dependency_dict["collection_id_child"])
                if child_solution.internal()['installed']:
                    children.append(str(dict_to_coordinates(child_solution.setup())))

            if children:
                module_logger().info("The following solutions depend on this installation: %s. Not uninstalling %s..."
                                     % (", ".join(children), str(resolve_result.coordinates())))
                if parent:
                    return

                raise RuntimeError(
                    "Cannot uninstall \"%s\". Other solution depend on this installation! "
                    "Inspect log for more information!"
                    % resolve_result.coordinates
                )

        remove_disc_content_from_solution(resolve_result.loaded_solution())
        EnvironmentManager.remove_disc_content_from_environment(environment)
        self.album.collection_manager().solutions().set_uninstalled(
            resolve_result.catalog(),
            resolve_result.loaded_solution().coordinates()
        )

        if rm_dep:  # remove dependencies (parent of the solution) last
            self._remove_dependencies(resolve_result.loaded_solution(), rm_dep)

        module_logger().info("Uninstalled \"%s\"!" % resolve_result.loaded_solution().coordinates().name())

    def _run_solution_uninstall_routine(self, active_solution: ISolution, environment: IEnvironment, argv):
        """Run uninstall routine of album if specified. Expects environment to be set!"""
        script_creator_un_install = ScriptCreatorUnInstall()

        if active_solution.setup().uninstall and callable(active_solution.setup().uninstall):
            module_logger().debug('Creating uninstall script...')
            script = script_creator_un_install.create_script(active_solution, argv)
            module_logger().debug('Calling uninstall routine specified in solution...')
            album_logging.configure_logging(active_solution.coordinates().name())
            self.album.environment_manager().run_scripts(environment, [script])
            album_logging.pop_active_logger()
        else:
            module_logger().info(
                'No \"uninstall\" routine configured for solution \"%s\"! Skipping...' %
                active_solution.coordinates().name()
            )

    def _remove_dependencies(self, solution: ISolution, rm_dep=False):
        parent = get_parent_dict(solution)
        if parent:
            # recursive call to remove the parent
            resolve_solution = build_resolve_string(parent)
            self._uninstall(resolve_solution, rm_dep)

    def clean_unfinished_installations(self):
        collection_solution_list = self.album.collection_manager().get_collection_index().get_unfinished_installation_solutions()
        for collection_solution in collection_solution_list:
            catalog = self.album.collection_manager().catalogs().get_by_id(collection_solution.internal()["catalog_id"])
            path = self.album.collection_manager().solutions().get_solution_file(
                catalog, dict_to_coordinates(collection_solution.setup())
            )
            coordinates = dict_to_coordinates(collection_solution.setup())

            resolve = ResolveResult(
                path=path,
                catalog=catalog,
                collection_entry=collection_solution,
                coordinates=coordinates
            )
            self.album.collection_manager().retrieve_and_load_resolve_result(resolve)

            self.album.collection_manager().solutions().set_cache_paths(resolve.loaded_solution(), resolve.catalog())

            # only remove environment when solution has its own environment
            if not get_parent_dict(resolve.loaded_solution()):
                self._clean_unfinished_installations_environment(resolve)

            remove_disc_content_from_solution(resolve.loaded_solution())

            self.album.collection_manager().solutions().set_uninstalled(resolve.catalog(), coordinates)

    def _clean_unfinished_installations_environment(self, resolve: IResolveResult):
        remove_status = False
        try:
            environment = self.album.environment_manager().set_environment(resolve.loaded_solution(), resolve.catalog())
            remove_status = self.album.environment_manager().remove_environment(environment)
        except LookupError:
            pass

        if not remove_status:
            # try to clean environment folder if exists
            environment_folder = self.album.environment_manager().get_environment_base_folder().joinpath(
                EnvironmentManager.get_environment_name(resolve.coordinates(), resolve.catalog())
            )
            force_remove(environment_folder)
