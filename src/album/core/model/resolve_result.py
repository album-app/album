"""Implementation of the ICollectionSolution class."""
from pathlib import Path
from typing import Optional

from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution


class ResolveResult(ICollectionSolution):
    def __init__(
        self,
        path: Path,
        catalog: ICatalog,
        collection_entry: Optional[ICollectionIndex.ICollectionSolution],
        coordinates: ICoordinates,
        loaded_solution: Optional[ISolution] = None,
        single_file_solution: bool = False,
    ):
        self._catalog: ICatalog = catalog
        self._path = path
        self._collection_entry = collection_entry
        self._coordinates = coordinates
        self._loaded_solution = loaded_solution
        self._is_single_file = single_file_solution

        if collection_entry and not loaded_solution:
            self._load_solution_from_collection_entry()

    def __eq__(self, other: object) -> bool:
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

    def database_entry(self) -> Optional[ICollectionIndex.ICollectionSolution]:
        return self._collection_entry

    def coordinates(self) -> ICoordinates:
        return self._coordinates

    def loaded_solution(self) -> ISolution:
        return self._loaded_solution

    def set_loaded_solution(self, loaded_solution: ISolution) -> None:
        self._loaded_solution = loaded_solution

    def set_coordinates(self, coordinates: ICoordinates) -> None:
        self._coordinates = coordinates

    def set_database_entry(
        self, database_entry: ICollectionIndex.ICollectionSolution
    ) -> None:
        self._collection_entry = database_entry

    def _load_solution_from_collection_entry(self) -> None:
        if not self._collection_entry:
            raise ValueError("No collection entry to load solution from.")

        attrs = self._collection_entry.setup()
        self.set_loaded_solution(Solution(attrs))

    def is_single_file(self) -> bool:
        return self._is_single_file
