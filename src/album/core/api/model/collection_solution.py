from abc import abstractmethod
from pathlib import Path

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution


class ICollectionSolution:
    @abstractmethod
    def catalog(self) -> ICatalog:
        raise NotImplementedError

    @abstractmethod
    def path(self) -> Path:
        raise NotImplementedError

    @abstractmethod
    def database_entry(self) -> ICollectionIndex.ICollectionSolution:
        raise NotImplementedError

    @abstractmethod
    def coordinates(self) -> ICoordinates:
        raise NotImplementedError

    @abstractmethod
    def loaded_solution(self) -> ISolution:
        raise NotImplementedError

    @abstractmethod
    def set_loaded_solution(self, loaded_solution):
        raise NotImplementedError

    @abstractmethod
    def set_coordinates(self, coordinates):
        raise NotImplementedError

    @abstractmethod
    def set_database_entry(self, database_entry: ICollectionIndex.ICollectionSolution):
        raise NotImplementedError
