from abc import ABCMeta, abstractmethod

from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.runner.core.api.model.coordinates import ICoordinates


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
    def load_or_create(self):
        raise NotImplementedError

    @abstractmethod
    def catalogs(self) -> ICatalogHandler:
        raise NotImplementedError

    @abstractmethod
    def solutions(self) -> ISolutionHandler:
        raise NotImplementedError

    @abstractmethod
    def get_index_as_dict(self):
        raise NotImplementedError

    @abstractmethod
    def resolve_installed(self, resolve_solution) -> ICollectionSolution:
        """Resolves an input. Expects solution to be installed.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url


        Returns:
            The resolve result, including the loaded solution.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_installed_and_load(self, resolve_solution) -> ICollectionSolution:
        """Resolves an input. Expects solution to be installed.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url


        Returns:
            The resolve result, including the loaded solution.
        """
        raise NotImplementedError

    @abstractmethod
    def resolve_and_load(self, resolve_solution) -> ICollectionSolution:
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
    def resolve_and_load_catalog_coordinates(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> ICollectionSolution:
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
    def resolve_and_load_coordinates(
        self, coordinates: ICoordinates
    ) -> ICollectionSolution:
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
    def resolve(self, resolve_solution) -> ICollectionSolution:
        """Resolves a string input and loads its content.

        Downloads a catalog if not already cached.

        Args:
            resolve_solution:
                What to resolve. Either path, doi, group:name:version, catalog:group:name:version, url

        Returns:
            The resolve result

        """
        raise NotImplementedError

    @abstractmethod
    def resolve_parent(self, parent_dict: dict) -> ICollectionSolution:
        raise NotImplementedError

    def get_collection_index(self) -> ICollectionIndex:
        raise NotImplementedError

    @abstractmethod
    def retrieve_and_load_resolve_result(self, resolve_result: ICollectionSolution):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def write_version_to_json(path, name, version) -> None:
        raise NotImplementedError
