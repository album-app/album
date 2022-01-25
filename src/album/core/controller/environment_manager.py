from pathlib import Path

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.environment import IEnvironment
from album.core.controller.conda_manager import CondaManager
from album.core.controller.mamba_manager import MambaManager
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import force_remove, remove_link
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import set_environment_paths
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class EnvironmentManager(IEnvironmentManager):

    def __init__(self, album: IAlbumController):
        self.conda_manager = CondaManager(album.configuration())
        self.mamba_manager = MambaManager(album.configuration())
        self.album = album

    def install_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        environment = Environment(
            collection_solution.loaded_solution().setup().dependencies,
            self.get_environment_name(collection_solution.coordinates(), collection_solution.catalog()),
            collection_solution.loaded_solution().installation().internal_cache_path()
        )
        self.mamba_manager.install(environment, collection_solution.loaded_solution().setup().album_api_version)
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def set_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        parent = collection_solution.database_entry().internal()['parent']
        # solution runs in its own environment
        if not parent:

            environment = Environment(
                dependencies_dict=None,
                environment_name=self.get_environment_name(collection_solution.coordinates(), collection_solution.catalog()),
                cache_path=collection_solution.loaded_solution().installation().internal_cache_path()
            )
            self.conda_manager.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            coordinates = dict_to_coordinates(parent.setup())
            catalog = self.album.catalogs().get_by_id(parent.internal()['catalog_id'])

            environment = Environment(
                None,
                self.get_environment_name(coordinates, catalog),
                collection_solution.loaded_solution().installation().internal_cache_path()
            )
            self.conda_manager.set_environment_path(environment)

        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def remove_environment(self, environment: IEnvironment) -> bool:
        """Removes an environment."""
        res = self.conda_manager.remove_environment(environment.name())
        self.remove_disc_content_from_environment(environment)
        return res

    def run_scripts(self, environment: IEnvironment, scripts, pipe_output=True):
        if environment:
            self.conda_manager.run_scripts(environment, scripts, pipe_output=pipe_output)
        else:
            raise EnvironmentError("Environment not set! Cannot run scripts!")

    def get_conda_manager(self):
        return self.conda_manager

    @staticmethod
    def get_environment_name(coordinates: ICoordinates, catalog: ICatalog) -> str:
        return "_".join([str(catalog.name()), coordinates.group(), coordinates.name(), coordinates.version()])

    @staticmethod
    def remove_disc_content_from_environment(environment: IEnvironment):
        remove_link(environment.path())
        remove_link(environment.cache_path())
