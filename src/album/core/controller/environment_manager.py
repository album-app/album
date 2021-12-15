from pathlib import Path

from album.core.api.album import IAlbum
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.environment import IEnvironment
from album.core.controller.conda_manager import CondaManager
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import set_environment_paths, get_parent_dict
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


class EnvironmentManager(IEnvironmentManager):

    def __init__(self, album: IAlbum):
        self.conda_manager = CondaManager(album.configuration())
        self.collection_manager = album.collection_manager()

    def install_environment(self, active_solution: ISolution, catalog: ICatalog) -> IEnvironment:
        environment = Environment(
            active_solution.setup().dependencies,
            self.get_environment_name(active_solution.coordinates(), catalog),
            active_solution.installation().package_path()
        )
        self.conda_manager.install(environment, active_solution.setup().album_api_version)
        set_environment_paths(active_solution, environment)
        return environment

    def set_environment(self, active_solution: ISolution, catalog: ICatalog) -> IEnvironment:
        parent = get_parent_dict(active_solution)
        # solution runs in its own environment
        if not parent:

            environment = Environment(
                None,
                self.get_environment_name(active_solution.coordinates(), catalog),
                active_solution.installation().package_path()
            )
            self.conda_manager.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            parent_resolve_result = self.collection_manager.resolve_parent(parent)

            environment = Environment(
                None,
                self.get_environment_name(parent_resolve_result.coordinates(), parent_resolve_result.catalog()),
                active_solution.installation().package_path()
            )
            self.conda_manager.set_environment_path(environment)

        set_environment_paths(active_solution, environment)
        return environment

    def set_environment_from_database(
            self, active_solution: ISolution, collection_entry: ICollectionIndex.ICollectionSolution, catalog: ICatalog
    ) -> IEnvironment:
        parent = collection_entry.internal()['parent']
        # solution runs in its own environment
        if not parent:

            environment = Environment(
                None,
                self.get_environment_name(active_solution.coordinates(), catalog),
                active_solution.installation().package_path()
            )
            self.conda_manager.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            coordinates = dict_to_coordinates(parent.setup())
            catalog = self.collection_manager.catalogs().get_by_id(parent.internal()['catalog_id'])

            environment = Environment(
                None,
                self.get_environment_name(coordinates, catalog),
                active_solution.installation().package_path()
            )
            self.conda_manager.set_environment_path(environment)

        set_environment_paths(active_solution, environment)
        return environment

    def remove_environment(self, environment: IEnvironment) -> bool:
        """Removes an environment."""
        return self.conda_manager.remove_environment(environment.name())

    def get_environment_base_folder(self) -> Path:
        return Path(self.conda_manager.get_base_environment_path())

    def run_scripts(self, environment: IEnvironment, scripts):
        if environment:
            self.conda_manager.run_scripts(environment, scripts)
        else:
            raise EnvironmentError("Environment not set! Cannot run scripts!")

    def get_conda_manager(self):
        return self.conda_manager

    @staticmethod
    def get_environment_name(coordinates: ICoordinates, catalog: ICatalog) -> str:
        return "_".join([str(catalog.name()), coordinates.group(), coordinates.name(), coordinates.version()])

    @staticmethod
    def remove_disc_content_from_environment(environment: IEnvironment):
        force_remove(environment.cache_path())
