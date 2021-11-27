from abc import ABCMeta, abstractmethod

from album.core.model.catalog import Catalog
from album.core.model.catalog_updates import SolutionChange
from album.runner.model.coordinates import Coordinates
from album.runner.model.solution import Solution


class SolutionInterface:
    __metaclass__ = ABCMeta

    @abstractmethod
    def add_or_replace(self, catalog: Catalog, active_solution: Solution, path):
        raise NotImplementedError

    @abstractmethod
    def set_uninstalled(self, catalog: Catalog, coordinates: Coordinates):
        raise NotImplementedError

    @abstractmethod
    def set_parent(self, catalog_parent: Catalog, catalog_child: Catalog, coordinates_parent: Coordinates,
                       coordinates_child: Coordinates):
        raise NotImplementedError

    @abstractmethod
    def remove_solution(self, catalog: Catalog, coordinates: Coordinates):
        raise NotImplementedError

    @abstractmethod
    def update_solution(self, catalog: Catalog, coordinates: Coordinates, attrs):
        raise NotImplementedError

    @abstractmethod
    def apply_change(self, catalog, change: SolutionChange):
        raise NotImplementedError

    @abstractmethod
    def set_installed(self, catalog: Catalog, coordinates: Coordinates):
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, catalog: Catalog, coordinates: Coordinates) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_solution_path(self, catalog: Catalog, coordinates: Coordinates):
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
    def get_solution_file(self, catalog: Catalog, coordinates: Coordinates):
        """Gets the file to the solution.py file of the extracted solution.zip living inside the catalog.

        Args:
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The path where the file is supposed to be once the zip is extracted during installation.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_zip(self, catalog: Catalog, coordinates: Coordinates):
        """Gets the cache zip of a solution given its group, name and version living inside the catalog.

        Args:
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the solution.py cache file.

        """
        raise NotImplementedError

    @abstractmethod
    def retrieve_solution(self, catalog: Catalog, coordinates: Coordinates):
        """Downloads or copies a solution from the catalog to the local resource (cache path of the catalog).

        Args:
            coordinates:
                The group affiliation, name, and version of the solution.
        Returns:
            The absolute path of the downloaded solution.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_zip_suffix(self, coordinates: Coordinates):
        """Gets the cache zip suffix of a solution given its group, name and version living inside the catalog.

        Args:
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The the cache zip suffix.

        """
        raise NotImplementedError

    @abstractmethod
    def set_cache_paths(self, solution: Solution, catalog):
        """Sets the available cache paths of the solution object, given its catalog_name (where it lives)."""
        raise NotImplementedError

    @abstractmethod
    def set_installation_unfinished(self, catalog: Catalog, coordinates: Coordinates):
        raise NotImplementedError
