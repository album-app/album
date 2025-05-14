"""This module contains the ICollectionSolution interface."""
from abc import abstractmethod
from pathlib import Path
from typing import Optional

from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex


class ICollectionSolution:
    """Class representing a solution in a collection."""

    @abstractmethod
    def catalog(self) -> ICatalog:
        """Return the catalog of the solution."""
        raise NotImplementedError

    @abstractmethod
    def path(self) -> Path:
        """Return the path to the solution."""
        raise NotImplementedError

    @abstractmethod
    def database_entry(self) -> Optional[ICollectionIndex.ICollectionSolution]:
        """Return the database entry of the solution if existed."""
        raise NotImplementedError

    @abstractmethod
    def coordinates(self) -> ICoordinates:
        """Return the coordinates of the solution."""
        raise NotImplementedError

    @abstractmethod
    def loaded_solution(self) -> ISolution:
        """Return the loaded solution."""
        raise NotImplementedError

    @abstractmethod
    def set_loaded_solution(self, loaded_solution: ISolution) -> None:
        """Set the loaded solution."""
        raise NotImplementedError

    @abstractmethod
    def set_coordinates(self, coordinates: ICoordinates) -> None:
        """Set the coordinates."""
        raise NotImplementedError

    @abstractmethod
    def set_database_entry(
        self, database_entry: ICollectionIndex.ICollectionSolution
    ) -> None:
        """Set the database entry."""
        raise NotImplementedError

    @abstractmethod
    def is_single_file(self) -> bool:
        """Return whether the solution is a single file solution."""
        raise NotImplementedError
