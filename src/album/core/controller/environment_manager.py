from pathlib import Path

from album.core.utils.operations.file_operations import force_remove

from album.core import Solution
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.conda_manager import CondaManager
from album.core.model.catalog import Catalog
from album.core.utils.operations.solution_operations import set_environment_paths, get_parent_dict
from album.runner.model.coordinates import Coordinates
from album.core.model.environment import Environment
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class EnvironmentManager(metaclass=Singleton):
    """Manages everything around the environment a solution lives in."""

    def __init__(self):
        self.conda_manager = CondaManager()
        self.collection_manager = CollectionManager()

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
        """Resolves the environment the active solution runs in.

        Returns the resolve result of the parent of the active solution.

        """
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
        """Returns the location all album-created environments live in."""
        return Path(self.conda_manager.get_base_environment_path())

    def run_scripts(self, environment: Environment, scripts):
        """Runs scripts in an environment"""
        if environment:
            self.conda_manager.run_scripts(environment, scripts)
        else:
            raise EnvironmentError("Environment not set! Cannot run scripts!")

    @staticmethod
    def get_environment_name(coordinates: Coordinates, catalog: Catalog):
        return "_".join([str(catalog.name), coordinates.group, coordinates.name, coordinates.version])

    @staticmethod
    def remove_disc_content_from_environment(environment: Environment):
        force_remove(environment.cache_path)
