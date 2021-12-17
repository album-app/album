from abc import ABCMeta, abstractmethod

from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_updates import ISolutionChange
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution


class ISolutionHandler:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_or_replace(self, catalog: ICatalog, active_solution: ISolution, path):
        raise NotImplementedError

    @abstractmethod
    def set_uninstalled(self, catalog: ICatalog, coordinates: ICoordinates):
        raise NotImplementedError

    @abstractmethod
    def set_parent(self, catalog_parent: ICatalog, catalog_child: ICatalog, coordinates_parent: ICoordinates,
                   coordinates_child: ICoordinates):
        raise NotImplementedError

    @abstractmethod
    def remove_parent(self, catalog: ICatalog, coordinates: ICoordinates):
        raise NotImplementedError

    @abstractmethod
    def remove_solution(self, catalog: ICatalog, coordinates: ICoordinates):
        raise NotImplementedError

    @abstractmethod
    def update_solution(self, catalog: ICatalog, coordinates: ICoordinates, attrs: dict):
        raise NotImplementedError

    @abstractmethod
    def apply_change(self, catalog: ICatalog, change: ISolutionChange):
        raise NotImplementedError

    @abstractmethod
    def set_installed(self, catalog: ICatalog, coordinates: ICoordinates):
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, catalog: ICatalog, coordinates: ICoordinates) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_solution_path(self, catalog: ICatalog, coordinates: ICoordinates):
        """Gets the cache path of a solution in a catalog given its group, name and version.

        Args:
            catalog:
                The catalog this solution lives in.
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_file(self, catalog: ICatalog, coordinates: ICoordinates):
        """Gets the file to the solution.py file of the extracted solution.zip living inside the catalog.

        Args:
            catalog:
                The catalog this solution belongs to.
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The path where the file is supposed to be once the zip is extracted during installation.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_zip(self, catalog: ICatalog, coordinates: ICoordinates):
        """Gets the cache zip of a solution given its group, name and version living inside the catalog.

        Args:
            catalog:
                The catalog this solution belongs to.
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the solution.py cache file.

        """
        raise NotImplementedError

    @abstractmethod
    def retrieve_solution(self, catalog: ICatalog, coordinates: ICoordinates):
        """Downloads or copies a solution from the catalog to the local resource (cache path of the catalog).

        Args:
            catalog:
                The catalog this solution belongs to.
            coordinates:
                The group affiliation, name, and version of the solution.
        Returns:
            The absolute path of the downloaded solution.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_zip_suffix(self, coordinates: ICoordinates):
        """Gets the cache zip suffix of a solution given its group, name and version living inside the catalog.

        Args:
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The the cache zip suffix.

        """
        raise NotImplementedError

    @abstractmethod
    def set_cache_paths(self, solution: ISolution, catalog: ICatalog):
        """Sets the available cache paths of the solution object, given its catalog_name (where it lives)."""
        raise NotImplementedError

    @abstractmethod
    def set_installation_unfinished(self, catalog: ICatalog, coordinates: ICoordinates):
        raise NotImplementedError
