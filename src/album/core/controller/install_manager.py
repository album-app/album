from typing import Optional

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.install_manager import IInstallManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.environment import IEnvironment
from album.core.controller.environment_manager import EnvironmentManager
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import remove_link
from album.core.utils.operations.resolve_operations import (
    clean_resolve_tmp,
    build_resolve_string,
    dict_to_coordinates,
)
from album.core.utils.operations.solution_operations import (
    get_deploy_dict,
    get_parent_dict,
)
from album.core.utils.operations.view_operations import get_solution_run_call_as_string
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.script_creator import (
    ScriptCreatorInstall,
    ScriptCreatorUnInstall,
)

module_logger = album_logging.get_active_logger


class InstallManager(IInstallManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def install(self, solution_to_resolve: str, argv=None):
        # this needs to happen before any (potentially not completely installed) solution is resolved
        self.clean_unfinished_installations()

        resolve_result = self.album.collection_manager().resolve_and_load(
            solution_to_resolve
        )
        self._install_resolve_result(resolve_result, argv, parent=False)

    def _resolve_result_is_installed(self, resolve_result: ICollectionSolution) -> bool:
        """Checks whether a resolve_result is already installed."""
        if resolve_result.database_entry():  # we know the solution is in the collection
            return (
                self.album.collection_manager()
                .get_collection_index()
                .is_installed(
                    resolve_result.catalog().catalog_id(), resolve_result.coordinates()
                )
            )
        return False

    def _install_resolve_result(
        self, resolve_result: ICollectionSolution, argv=None, parent=False
    ):
        """Installs a resolve result.

        CAUTION: Solution must be loaded!
        """
        # Load solution
        if not resolve_result.catalog():
            raise RuntimeError(
                "Solution cannot be installed without being associated with a catalog!"
            )
        elif not parent and self._resolve_result_is_installed(resolve_result):
            raise RuntimeError("Solution already installed. Uninstall solution first!")
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
        self._install_active_solution(resolve_result, argv)

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
        """Registers a resolve result in the collection"""
        # register in collection
        if resolve_result.catalog().is_cache():
            # a cache catalog is living in the collection so no need to update, we can add it directly
            self.album.solutions().add_to_cache_catalog(
                resolve_result.loaded_solution(),
                resolve_result.path().parent,  # the directory holding the solution file
            )
        else:
            # update the collection holding the solution entry
            self._update_in_collection_index(resolve_result)
        resolve_result.set_database_entry(
            self.album.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                resolve_result.catalog().catalog_id(), resolve_result.coordinates()
            )
        )

    def _remove_parent(self, resolve_result: ICollectionSolution):
        """Sets the parent of a solution"""
        self.album.solutions().remove_parent(
            resolve_result.catalog(), resolve_result.coordinates()
        )

    def _update_in_collection_index(self, resolve_result: ICollectionSolution):
        """Updates the collection entry of the resolved solution"""
        # update the solution in the collection
        self.album.solutions().update_solution(
            resolve_result.catalog(),
            resolve_result.coordinates(),
            get_deploy_dict(resolve_result.loaded_solution()),
        )

    def _install_active_solution(
        self, collection_solution: ICollectionSolution, argv=None
    ) -> Optional[ICollectionSolution]:
        """Installation routine for a loaded solution."""
        # install environment
        if argv is None:
            argv = [""]

        parent_resolve_result = None

        parent = get_parent_dict(collection_solution.loaded_solution())
        if parent:
            # install dependencies first. Recursive call to install with dependencies
            try:
                parent_resolve_result = self._install_parent(parent)
            except Exception as e:
                module_logger().error("Exception when installing parent:")
                raise e

            if parent_resolve_result:
                self.album.solutions().set_parent(
                    parent_resolve_result.database_entry(),
                    collection_solution.database_entry(),
                )
            else:
                self._remove_parent(collection_solution)

            collection_solution.set_database_entry(
                self.album.collection_manager()
                .get_collection_index()
                .get_solution_by_catalog_grp_name_version(
                    collection_solution.catalog().catalog_id(),
                    collection_solution.coordinates(),
                )
            )

            # resolve environment - at this point all parents should be already installed
            environment = self.album.environment_manager().set_environment(
                collection_solution
            )
        else:
            environment = self.album.environment_manager().install_environment(
                collection_solution
            )

        self._run_solution_install_routine(
            collection_solution.loaded_solution(), environment, argv
        )

        return parent_resolve_result

    def _run_solution_install_routine(
        self, active_solution: ISolution, environment: IEnvironment, argv
    ):
        """Run install routine of album if specified"""
        script_creator_install = ScriptCreatorInstall()

        if active_solution.setup().install and callable(
            active_solution.setup().install
        ):
            module_logger().debug("Creating install script...")
            script = script_creator_install.create_script(active_solution, argv)
            module_logger().debug("Calling install routine specified in solution...")
            self.album.environment_manager().run_scripts(environment, [script])
        else:
            module_logger().debug(
                'No "install" routine configured for solution "%s". Skipping...'
                % active_solution.coordinates().name()
            )

    def _install_parent(self, parent_dict: dict) -> ICollectionSolution:
        """Installs a parent of a solution given its description as a dictionary."""
        resolve_solution = build_resolve_string(parent_dict)
        resolve_result = self.album.collection_manager().resolve_and_load(
            resolve_solution
        )

        # recursive installation call. Not failing for already installed solutions. parent set to "True"
        self._install_resolve_result(resolve_result, parent=True)
        return resolve_result

    def uninstall(self, solution_to_resolve: str, rm_dep=False, argv=None):
        """Internal installation entry point for `uninstall` subcommand of `album`."""

        resolve_result = self.album.collection_manager().resolve_installed_and_load(
            solution_to_resolve
        )

        module_logger().info(
            'Uninstalling "%s"...' % resolve_result.coordinates().name()
        )

        if argv is None:
            argv = [""]

        parent = resolve_result.database_entry().internal()["parent"]
        # get the environment
        environment = None
        try:
            environment = self.album.environment_manager().set_environment(
                resolve_result
            )
            self._run_solution_uninstall_routine(
                resolve_result.loaded_solution(), environment, argv
            )

            if not parent:
                self.album.environment_manager().remove_environment(environment)

        except LookupError:
            # environment might have been deleted manually
            pass
        finally:
            if environment and not parent:
                EnvironmentManager.remove_disc_content_from_environment(environment)

        if resolve_result.database_entry().internal()["children"]:
            children = []
            for dependency_dict in resolve_result.database_entry().internal()[
                "children"
            ]:
                # get the child entry
                child_solution = (
                    self.album.collection_manager()
                    .get_collection_index()
                    .get_solution_by_collection_id(
                        dependency_dict["collection_id_child"]
                    )
                )
                if child_solution.internal()["installed"]:
                    children.append(str(dict_to_coordinates(child_solution.setup())))

            if children:
                module_logger().info(
                    "The following solutions depend on this installation: %s. Not uninstalling %s..."
                    % (", ".join(children), str(resolve_result.coordinates()))
                )
                if parent:
                    return

                raise RuntimeError(
                    'Cannot uninstall "%s". Other solution depend on this installation! '
                    "Inspect log for more information!" % resolve_result.coordinates()
                )

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

    def _run_solution_uninstall_routine(
        self, active_solution: ISolution, environment: IEnvironment, argv
    ):
        """Run uninstall routine of album if specified. Expects environment to be set!"""
        script_creator_un_install = ScriptCreatorUnInstall()

        if active_solution.setup().uninstall and callable(
            active_solution.setup().uninstall
        ):
            module_logger().debug("Creating uninstall script...")
            script = script_creator_un_install.create_script(active_solution, argv)
            module_logger().debug("Calling uninstall routine specified in solution...")
            album_logging.configure_logging("uninstall")
            self.album.environment_manager().run_scripts(environment, [script])
            album_logging.pop_active_logger()
        else:
            module_logger().debug(
                'No "uninstall" routine configured for solution "%s"! Skipping...'
                % active_solution.coordinates().name()
            )

    def _remove_dependencies(self, solution: ISolution, rm_dep=False):
        parent = get_parent_dict(solution)
        if parent:
            # recursive call to remove the parent
            resolve_solution = build_resolve_string(parent)
            self.uninstall(resolve_solution, rm_dep)

    def clean_unfinished_installations(self):
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

    def _clean_unfinished_installations_environment(self, resolve: ICollectionSolution):
        try:
            environment = self.album.environment_manager().set_environment(resolve)
            self.album.environment_manager().remove_environment(environment)
        except LookupError:
            pass

    def _remove_disc_content_from_solution(self, resolve_result: ICollectionSolution):
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
