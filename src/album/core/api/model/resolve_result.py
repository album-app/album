from abc import abstractmethod
from pathlib import Path

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution


class IResolveResult:

    @abstractmethod
    def catalog(self) -> ICatalog:
        raise NotImplementedError

    @abstractmethod
    def path(self) -> Path:
        raise NotImplementedError

    @abstractmethod
    def collection_entry(self) -> ICollectionIndex.ICollectionSolution:
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
