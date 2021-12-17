from pathlib import Path

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.resolve_result import IResolveResult
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution


class ResolveResult(IResolveResult):
    def __init__(self, path, catalog: ICatalog, collection_entry: ICollectionIndex.ICollectionSolution,
                 coordinates: ICoordinates, loaded_solution=None):
        self._catalog: ICatalog = catalog
        self._path = path
        self._collection_entry: ICollectionIndex.ICollectionSolution = collection_entry
        self._coordinates: ICoordinates = coordinates
        self._loaded_solution: ISolution = loaded_solution

    def __eq__(self, other):
        return isinstance(other, IResolveResult) and \
               other.catalog() == self._catalog and \
               other.path() == self._path and \
               other.loaded_solution() == self._loaded_solution and \
               other.collection_entry() == self._collection_entry and \
               other.coordinates() == self._coordinates

    def catalog(self) -> ICatalog:
        return self._catalog

    def path(self) -> Path:
        return self._path

    def collection_entry(self) -> ICollectionIndex.ICollectionSolution:
        return self._collection_entry

    def coordinates(self) -> ICoordinates:
        return self._coordinates

    def loaded_solution(self) -> ISolution:
        return self._loaded_solution

    def set_loaded_solution(self, loaded_solution):
        self._loaded_solution = loaded_solution

    def set_coordinates(self, coordinates):
        self._coordinates = coordinates
