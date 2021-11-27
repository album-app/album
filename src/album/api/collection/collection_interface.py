from abc import ABCMeta, abstractmethod

from album.core.model.collection_index import CollectionIndex

from album.api.collection.catalog_interface import CatalogInterface
from album.api.collection.solution_interface import SolutionInterface
from album.core.model.catalog import Catalog
from album.core.model.resolve_result import ResolveResult
from album.runner.model.coordinates import Coordinates


class CollectionInterface:
    """The Album Catalog Collection class.

    An album framework installation instance can hold arbitrarily many catalogs. This class holds all configured
    catalogs in memory and is mainly responsible to resolve (look up) solutions in all these catalogs.
    It is not responsible for resolving local paths and files or remembering what is already installed!
    Please use the resolve manager for this!
    Additionally, catalogs can be configured via this class.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def load_or_create_collection(self):
        raise NotImplementedError

    @abstractmethod
    def catalogs(self) -> CatalogInterface:
        raise NotImplementedError

    @abstractmethod
    def solutions(self) -> SolutionInterface:
        raise NotImplementedError

    @abstractmethod
    def add_solution_to_local_catalog(self, active_solution, path):
        """Force adds the installation to the local catalog to be cached for running"""
        raise NotImplementedError

    @abstractmethod
    def get_index_as_dict(self):
        raise NotImplementedError

    @abstractmethod
    def resolve_require_installation(self, resolve_solution) -> ResolveResult:
        """Resolves an input. Expects solution to be installed.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url


        Returns:
            The resolve result, including the loaded solution.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_require_installation_and_load(self, resolve_solution) -> ResolveResult:
        """Resolves an input. Expects solution to be installed.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url


        Returns:
            The resolve result, including the loaded solution.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_download_and_load(self, resolve_solution) -> ResolveResult:
        """Resolves a string input and loads its content.

        Downloads a catalog if not already cached.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url

        Returns:
            The resolve result, including the loaded solution.

        """
        raise NotImplementedError

    @abstractmethod
    def resolve_download_and_load_catalog_coordinates(self, catalog: Catalog, coordinates: Coordinates) -> ResolveResult:
        """Resolves a string input and loads its content.

        Downloads a catalog if not already cached.

        Args:
            catalog:
                Catalog to resolve in.
            coordinates:
                Coordinates to resolve.

        Returns:
            The resolve result, including the loaded solution.

        """
        raise NotImplementedError

    @abstractmethod
    def resolve_download_and_load_coordinates(self, coordinates: Coordinates) -> ResolveResult:
        """Resolves a string input and loads its content.

        Downloads a catalog if not already cached.

        Args:
            coordinates:
                Coordinates to resolve.

        Returns:
            The resolve result, including the loaded solution.

        """
        raise NotImplementedError

    @abstractmethod
    def resolve_download(self, resolve_solution) -> ResolveResult:
        """Resolves a string input and loads its content.

        Downloads a catalog if not already cached.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url

        Returns:
            list with resolve result and loaded album.

        """
        raise NotImplementedError

    @abstractmethod
    def resolve_parent(self, parent_dict: dict) -> ResolveResult:
        raise NotImplementedError

    def get_collection_index(self) -> CollectionIndex:
        raise NotImplementedError

    @abstractmethod
    def retrieve_and_load_resolve_result(self, resolve_result: ResolveResult):
        raise NotImplementedError

