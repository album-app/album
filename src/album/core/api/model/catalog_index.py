from abc import ABCMeta, abstractmethod
from typing import Optional, List

from album.core.api.model.database import IDatabase
from album.runner.core.api.model.coordinates import ICoordinates


class ICatalogIndex(IDatabase):
    """Interface handling the index of all solutions in a catalog."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def is_empty(self, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def update_name_version(self, name: str, version: str, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_name(self, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_version(self, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_all_solutions(self, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_solution(self, solution_id: int, close: bool = True) -> Optional[dict]:
        raise NotImplementedError

    def get_solution_by_coordinates(
        self, coordinates: ICoordinates, close: bool = True
    ) -> Optional[dict]:
        """Resolves a solution by its name, version and group.

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
    def get_solution_by_doi(self, doi: str, close: bool = True) -> Optional[dict]:
        """Resolves a solution by its DOI.

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
    ) -> Optional[List[dict]]:
        raise NotImplementedError

    @abstractmethod
    def remove_solution(self, solution_id: int, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def remove_solution_by_group_name_version(
        self, coordinates: ICoordinates, close: bool = True
    ):
        raise NotImplementedError

    @abstractmethod
    def update(
        self, coordinates: ICoordinates, solution_attrs: dict, close: bool = True
    ):
        """Updates a catalog to include a solution as a node with the attributes given.
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
        raise NotImplementedError

    @abstractmethod
    def export(self, path, export_format="JSON", close: bool = True):
        """Exports the index tree to disk.

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
