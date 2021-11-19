from album.core import Solution
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.conda_manager import CondaManager
from album.core.model.catalog import Catalog
from album.core.model.coordinates import Coordinates
from album.core.model.environment import Environment
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class EnvironmentManager(metaclass=Singleton):

    def __init__(self):
        self.conda_manager = CondaManager()
        self.collection_manager = CollectionManager()

    def install_environment(self, active_solution: Solution, catalog: Catalog):
        environment = Environment(
            active_solution.dependencies,
            self.get_environment_name(active_solution.coordinates, catalog),
            active_solution.package_path
        )
        self.conda_manager.install(environment, active_solution.album_version)

        active_solution.environment = environment

    def set_environment(self, active_solution: Solution, catalog: Catalog):
        """Resolves the environment the active solution runs in.

        Returns the resolve result of the parent of the active solution.

        """
        # solution runs in its own environment
        if not active_solution.parent:

            environment = Environment(
                None,
                self.get_environment_name(active_solution.coordinates, catalog),
                active_solution.package_path
            )
            self.conda_manager.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            parent_resolve_result = self.collection_manager.resolve_parent(active_solution.parent)

            environment = Environment(
                None,
                self.get_environment_name(parent_resolve_result.coordinates, parent_resolve_result.catalog),
                active_solution.package_path
            )
            self.conda_manager.set_environment_path(environment)

        active_solution.environment = environment

    @staticmethod
    def get_environment_name(coordinates: Coordinates, catalog: Catalog):
        return "_".join([str(catalog.name), coordinates.group, coordinates.name, coordinates.version])