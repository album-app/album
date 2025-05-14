"""Solution handler interface."""
from abc import ABCMeta, abstractmethod
from pathlib import Path

from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_updates import ISolutionChange
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.link import Link


class ISolutionHandler:
    """Interface for the solution handler."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def add_or_replace(self, catalog: ICatalog, solution: ICollectionSolution):
        """Add or replace a solution in a catalog."""
        raise NotImplementedError

    @abstractmethod
    def add_to_cache_catalog(self, solution: ICollectionSolution) -> None:
        """Force add the installation to the local catalog to be cached for running."""
        raise NotImplementedError

    @abstractmethod
    def set_uninstalled(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        """Set the installation status of a solution to uninstalled."""
        raise NotImplementedError

    @abstractmethod
    def set_parent(
        self,
        parent: ICollectionIndex.ICollectionSolution,
        child: ICollectionIndex.ICollectionSolution,
    ) -> None:
        """Set the parent of a solution in a catalog."""
        raise NotImplementedError

    @abstractmethod
    def remove_parent(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        """Remove the parent of a solution in a catalog."""
        raise NotImplementedError

    @abstractmethod
    def remove_solution(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        """Remove a solution from a catalog."""
        raise NotImplementedError

    @abstractmethod
    def update_solution(
        self, catalog: ICatalog, coordinates: ICoordinates, attrs: dict
    ) -> None:
        """Update a solution in a catalog."""
        raise NotImplementedError

    @abstractmethod
    def apply_change(
        self, catalog: ICatalog, change: ISolutionChange, override: bool
    ) -> None:
        """Apply a change to a solution in a catalog."""
        raise NotImplementedError

    @abstractmethod
    def set_installed(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        """Set the installation status of a solution to instal."""
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, catalog: ICatalog, coordinates: ICoordinates) -> bool:
        """Check if a solution is installed in a catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_package_path(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> Link:
        """Get the cache path of a solution in a catalog given its group, name and version.

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
    def get_solution_installation_path(
        self, catalog: ICatalog, coordinates: ICoordinates
    ):
        """Get the path of files belonging to an installed solution in a catalog given its group, name and version.

        Args:
            catalog:
                The catalog this solution lives in.
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the installation folder of the solution.

        """
        raise NotImplementedError

    @abstractmethod
    def get_solution_file(self, catalog: ICatalog, coordinates: ICoordinates) -> Path:
        """Get the file to the solution.py file of the extracted solution.zip living inside the catalog.

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
    def retrieve_solution(self, catalog: ICatalog, coordinates: ICoordinates) -> Path:
        """Download or copy a solution from the catalog to the local resource (cache path of the catalog).

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
    def get_solution_zip_suffix(self, coordinates: ICoordinates) -> Path:
        """Get the cache zip suffix of a solution given its group, name and version living inside the catalog.

        Args:
            coordinates:
                The group affiliation, name, and version of the solution.

        Returns:
            The the cache zip suffix.

        """
        raise NotImplementedError

    @abstractmethod
    def set_cache_paths(self, solution: ISolution, catalog: ICatalog) -> None:
        """Set the available cache paths of the solution object, given its catalog_name (where it lives)."""
        raise NotImplementedError

    @abstractmethod
    def set_installation_unfinished(self, catalog: ICatalog, coordinates: ICoordinates):
        """Set the installation status of a solution to unfinished."""
        raise NotImplementedError
