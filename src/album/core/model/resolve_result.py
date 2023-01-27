from pathlib import Path

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution


class ResolveResult(ICollectionSolution):
    def __init__(
        self,
        path,
        catalog: ICatalog,
        collection_entry: ICollectionIndex.ICollectionSolution,
        coordinates: ICoordinates,
        loaded_solution=None,
    ):
        self._catalog: ICatalog = catalog
        self._path = path
        self._collection_entry: ICollectionIndex.ICollectionSolution = collection_entry
        self._coordinates: ICoordinates = coordinates
        self._loaded_solution: ISolution = loaded_solution

        if collection_entry and not loaded_solution:
            self._load_solution_from_collection_entry()

    def __eq__(self, other):
        return (
            isinstance(other, ICollectionSolution)
            and other.catalog() == self._catalog
            and other.path() == self._path
            and other.loaded_solution() == self._loaded_solution
            and other.database_entry() == self._collection_entry
            and other.coordinates() == self._coordinates
        )

    def catalog(self) -> ICatalog:
        return self._catalog

    def path(self) -> Path:
        return self._path

    def database_entry(self) -> ICollectionIndex.ICollectionSolution:
        return self._collection_entry

    def coordinates(self) -> ICoordinates:
        return self._coordinates

    def loaded_solution(self) -> ISolution:
        return self._loaded_solution

    def set_loaded_solution(self, loaded_solution):
        self._loaded_solution = loaded_solution

    def set_coordinates(self, coordinates):
        self._coordinates = coordinates

    def set_database_entry(self, database_entry: ICollectionIndex.ICollectionSolution):
        self._collection_entry = database_entry

    def _load_solution_from_collection_entry(self):
        attrs = self._collection_entry.setup()
        self.set_loaded_solution(Solution(attrs))
