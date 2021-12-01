from pathlib import Path

from album.api.album_interface import AlbumInterface
from album.api.environment_interface import EnvironmentInterface
from album.core.controller.conda_manager import CondaManager
from album.core.model.catalog import Catalog
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.solution_operations import set_environment_paths, get_parent_dict
from album.runner import album_logging
from album.runner.model.coordinates import Coordinates
from album.runner.model.solution import Solution

module_logger = album_logging.get_active_logger


class EnvironmentManager(EnvironmentInterface):

    def __init__(self, album: AlbumInterface):
        self.conda_manager = CondaManager(album.configuration())
        self.collection_manager = album.collection_manager()

    def install_environment(self, active_solution: Solution, catalog: Catalog) -> Environment:
        environment = Environment(
            active_solution.setup.dependencies,
            self.get_environment_name(active_solution.coordinates, catalog),
            active_solution.installation.package_path
        )
        self.conda_manager.install(environment, active_solution.setup.album_api_version)
        set_environment_paths(active_solution, environment)
        return environment

    def set_environment(self, active_solution: Solution, catalog: Catalog) -> Environment:
        parent = get_parent_dict(active_solution)
        # solution runs in its own environment
        if not parent:

            environment = Environment(
                None,
                self.get_environment_name(active_solution.coordinates, catalog),
                active_solution.installation.package_path
            )
            self.conda_manager.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            parent_resolve_result = self.collection_manager.resolve_parent(parent)

            environment = Environment(
                None,
                self.get_environment_name(parent_resolve_result.coordinates, parent_resolve_result.catalog),
                active_solution.installation.package_path
            )
            self.conda_manager.set_environment_path(environment)

        set_environment_paths(active_solution, environment)
        return environment

    def remove_environment(self, environment: Environment) -> bool:
        """Removes an environment."""
        return self.conda_manager.remove_environment(environment.name)

    def get_environment_base_folder(self):
        return Path(self.conda_manager.get_base_environment_path())

    def run_scripts(self, environment: Environment, scripts):
        if environment:
            self.conda_manager.run_scripts(environment, scripts)
        else:
            raise EnvironmentError("Environment not set! Cannot run scripts!")

    def get_conda_manager(self):
        return self.conda_manager

    @staticmethod
    def get_environment_name(coordinates: Coordinates, catalog: Catalog):
        return "_".join([str(catalog.name), coordinates.group, coordinates.name, coordinates.version])

    @staticmethod
    def remove_disc_content_from_environment(environment: Environment):
        force_remove(environment.cache_path)
