"""Module for the collection index interface."""
from abc import ABCMeta, abstractmethod
from typing import Any, Dict, List, Optional

from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.model.database import IDatabase


class ICollectionIndex(IDatabase):
    """Interface for the collection index."""

    __metaclass__ = ABCMeta

    class ICollectionSolution:
        """Interface for a solution in a collection."""

        __metaclass__ = ABCMeta

        @abstractmethod
        def setup(self) -> Dict[str, Any]:
            """Return the setup of the solution."""
            raise NotImplementedError

        def internal(self) -> Dict[str, Any]:
            """Return the internal data of the solution."""
            raise NotImplementedError

    @abstractmethod
    def create(self) -> None:
        """Create the collection index."""
        raise NotImplementedError

    @abstractmethod
    def update_name_version(self, name: str, version: str, close: bool = True) -> None:
        """Update the name and version of the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_name(self, close: bool = True) -> str:
        """Return the name of the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_version(self, close: bool = True) -> str:
        """Return the version of the collection index."""
        raise NotImplementedError

    @abstractmethod
    def is_empty(self, close: bool = True) -> bool:
        """Return whether the collection index is empty."""
        raise NotImplementedError

    @abstractmethod
    def insert_catalog(
        self,
        name: str,
        src: str,
        path: str,
        deletable: bool,
        branch_name: str,
        catalog_type: str,
        close: bool = True,
    ) -> int:
        """Insert a catalog into the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog(
        self, catalog_id: int, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Return a catalog from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_by_name(
        self, catalog_name: str, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Return a catalog from the collection index by name."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_by_path(
        self, catalog_path: str, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Return a catalog from the collection index by path."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_by_src(
        self, catalog_src: str, close: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Return a catalog from the collection index by source."""
        raise NotImplementedError

    @abstractmethod
    def get_all_catalogs(self, close: bool = True) -> List[Dict[str, Any]]:
        """Return all catalogs from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def remove_catalog(self, catalog_id: int, close: bool = True) -> None:
        """Remove a catalog from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def insert_solution(
        self, catalog_id: int, solution_attrs: Dict[str, Any], close: bool = True
    ) -> int:
        """Insert a solution into the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_all_solutions(self, close: bool = True) -> List[ICollectionSolution]:
        """Return all solutions from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_all_installed_solutions_by_catalog(
        self, catalog_id, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all installed solutions from the collection index of a certain catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_catalog(
        self, catalog_id, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all solutions from the collection index of a certain catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_hash(
        self, hash_value, close: bool = True
    ) -> Optional[ICollectionSolution]:
        """Return a solution from the collection index by hash."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_collection_id(
        self, collection_id, close: bool = True
    ) -> Optional[ICollectionSolution]:
        """Return a solution from the collection index by collection id."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_doi(
        self, doi, close: bool = True
    ) -> Optional[ICollectionSolution]:
        """Return a solution from the collection index by DOI."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_catalog_grp_name_version(
        self, catalog_id, coordinates: ICoordinates, close: bool = True
    ) -> Optional[ICollectionSolution]:
        """Return a solution from the collection index by catalog and coordinates."""
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_grp_name_version(
        self, coordinates: ICoordinates, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all solutions from the collection index by coordinates."""
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_name_version(
        self, name: str, version: str, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all solutions from the collection index by name and version."""
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_grp_name(
        self, group: str, name: str, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all solutions from the collection index by group and name."""
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_name(
        self, name: str, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all solutions from the collection index by name."""
        raise NotImplementedError

    @abstractmethod
    def get_recently_installed_solutions(
        self, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all recently installed solutions from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_recently_launched_solutions(
        self, close: bool = True
    ) -> List[ICollectionSolution]:
        """Return all recently launched solutions from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def get_unfinished_installation_solutions(self, close: bool = True):
        """Return all unfinished installation solutions from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def update_solution(
        self,
        catalog_id,
        coordinates: ICoordinates,
        solution_attrs: dict,
        supported_attrs: list,
        close: bool = True,
    ):
        """Update a solution in the collection index."""
        raise NotImplementedError

    @abstractmethod
    def add_or_replace_solution(
        self, catalog_id, coordinates: ICoordinates, solution_attrs, close: bool = True
    ):
        """Add or replace a solution in the collection index."""
        raise NotImplementedError

    @abstractmethod
    def remove_solution(
        self, catalog_id, coordinates: ICoordinates, close: bool = True
    ):
        """Remove a solution from the collection index."""
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, catalog_id, coordinates: ICoordinates, close: bool = True):
        """Return whether a solution is installed."""
        raise NotImplementedError

    @abstractmethod
    def insert_collection_collection(
        self,
        collection_id_parent,
        collection_id_child,
        catalog_id_parent,
        catalog_id_child,
        close=True,
    ):
        """Insert a collection into a collection."""
        raise NotImplementedError

    @abstractmethod
    def remove_parent(self, collection_id, close=True):
        """Remove a parent collection."""
        raise NotImplementedError
