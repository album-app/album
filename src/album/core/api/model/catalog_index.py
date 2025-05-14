"""This module contains the interface for the Catalog Index class."""
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.model.database import IDatabase


class ICatalogIndex(IDatabase):
    """Interface handling the index of all solutions in a catalog."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def create(self) -> None:
        """Create the index table."""
        raise NotImplementedError

    @abstractmethod
    def is_empty(self, close: bool = True) -> bool:
        """Check if the index is empty."""
        raise NotImplementedError

    @abstractmethod
    def update_name_version(self, name: str, version: str, close: bool = True) -> None:
        """Update the name and version of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_name(self, close: bool = True) -> Optional[str]:
        """Get the name of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_version(self, close: bool = True) -> Optional[str]:
        """Get the version of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_all_solutions(self, close: bool = True) -> List[Dict[str, Any]]:
        """Get all solutions in the index."""
        raise NotImplementedError

    @abstractmethod
    def get_solution(
        self, solution_id: int, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get a solution by its id."""
        raise NotImplementedError

    def get_solution_by_coordinates(
        self, coordinates: ICoordinates, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Resolve a solution by its name, version and group.

        Args:
            close:
                if specified closes the connection after execution
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            None or row not found.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_doi(
        self, doi: str, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Resolve a solution by its DOI.

        Args:
            close:
                if specified closes the connection after execution
            doi:
                The doi to resolve for.

        Returns:
            None or a node if any found.

        Raises:
            RuntimeError if the DOI was found more than once.
                         if the node found is not a leaf

        """
        raise NotImplementedError

    def get_all_solution_versions(
        self, group: str, name: str, close: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all versions of a solution."""
        raise NotImplementedError

    @abstractmethod
    def remove_solution(self, solution_id: int, close: bool = True) -> None:
        """Remove a solution by its id."""
        raise NotImplementedError

    @abstractmethod
    def remove_solution_by_group_name_version(
        self, coordinates: ICoordinates, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Remove a solution by its group, name, and version."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        coordinates: ICoordinates,
        solution_attrs: Dict[str, Any],
        close: bool = True,
    ) -> None:
        """Update a catalog to include a solution as a node with the attributes given.

         Updates exiting nodes if node already present in tree.

        Args:
            close:
                if specified closes the connection after execution
            coordinates:
                The coordinates of the solution.
            solution_attrs:
                The solution attributes. Must hold group, name, version.

        """
        raise NotImplementedError

    @abstractmethod
    def save(self):
        """Save the index database to disk."""
        raise NotImplementedError

    @abstractmethod
    def export(
        self, path: Union[str, Path], export_format: str = "JSON", close: bool = True
    ) -> None:
        """Export the index database to disk.

        Args:
            close:
                if specified closes the connection after execution
            path:
                The path to store the export to.
            export_format:
                The format to save to. Choose from ["JSON"]. (Default: JSON)

        Raises:
            NotImplementedError if the format is not supported.

        """
        raise NotImplementedError
