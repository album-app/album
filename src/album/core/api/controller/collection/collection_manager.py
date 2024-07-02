"""The Album Catalog Collection interface class."""
from abc import ABCMeta, abstractmethod
from typing import Any, Dict

from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution


class ICollectionManager:
    """The Album Catalog Collection class.

    An album framework installation instance can hold arbitrarily many catalogs. This class holds all configured
    catalogs in memory and is mainly responsible to resolve (look up) solutions in all these catalogs.
    It is not responsible for resolving local paths and files or remembering what is already installed!
    Please use the resolve manager for this!
    Additionally, catalogs can be configured via this class.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def load_or_create(self) -> None:
        """Load or create the collection."""
        raise NotImplementedError

    @abstractmethod
    def catalogs(self) -> ICatalogHandler:
        """Get the catalog handler."""
        raise NotImplementedError

    @abstractmethod
    def solutions(self) -> ISolutionHandler:
        """Get the solution handler."""
        raise NotImplementedError

    @abstractmethod
    def get_index_as_dict(self) -> Dict[str, Any]:
        """Get the index as a dictionary."""
        raise NotImplementedError

    @abstractmethod
    def resolve_installed(self, resolve_solution: str) -> ICollectionSolution:
        """Resolve an input. Expect solution to be installed.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url


        Returns:
            The resolve result, including the loaded solution.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_installed_and_load(self, resolve_solution: str) -> ICollectionSolution:
        """Resolve an input. Expect solution to be installed.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url


        Returns:
            The resolve result, including the loaded solution.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_and_load_catalog_coordinates(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> ICollectionSolution:
        """Resolve a solution in a given catalog."""
        raise NotImplementedError

    @abstractmethod
    def resolve_and_load_coordinates(
        self, coordinates: ICoordinates
    ) -> ICollectionSolution:
        """Resolve a solution in all available catalogs."""
        raise NotImplementedError

    @abstractmethod
    def resolve_and_load(self, resolve_solution: str) -> ICollectionSolution:
        """Resolve a string input and load its content.

        Downloads a catalog if not already cached.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url

        Returns:
            The resolve result, including the loaded solution.

        """
        raise NotImplementedError

    @abstractmethod
    def resolve(self, str_input: str) -> ICollectionSolution:
        """Resolve a string input and load its content.

        Downloads a catalog if not already cached.

        Args:
            str_input:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url

        Returns:
            The resolve result

        """
        raise NotImplementedError

    @abstractmethod
    def get_collection_index(self) -> ICollectionIndex:
        """Get the collection index."""
        raise NotImplementedError

    @abstractmethod
    def retrieve_and_load_resolve_result(
        self, resolve_result: ICollectionSolution
    ) -> None:
        """Retrieve and load a resolve result."""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def write_version_to_json(path, name, version) -> None:
        """Write the version to a json file."""
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """Close the collection."""
        raise NotImplementedError
