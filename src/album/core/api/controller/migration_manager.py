"""Interface for handling the migration of indices."""
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, Tuple

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.mmversion import IMMVersion


class IMigrationManager:
    """Interface handling the migration from Indices of different versions.

    Responsible for execution of SQL migration!

    Tries to always migrate the catalog index or collection index to the current framework version
    able to deal with the database.

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def migrate_collection_index(
        self, collection_index: ICollectionIndex, initial_version
    ) -> None:
        """Migrate a collection index database to the target version."""
        raise NotImplementedError

    @abstractmethod
    def migrate_catalog_collection_db(
        self,
        collection_index_path: Path,
        curr_version: IMMVersion,
        target_version: IMMVersion,
    ) -> Path:
        """Migrate a given collection index to the target version."""
        raise NotImplementedError

    @abstractmethod
    def migrate_catalog_index_db(
        self,
        catalog_index_path: Path,
        curr_version: IMMVersion,
        target_version: IMMVersion,
    ) -> Path:
        """Migrate the index of a given catalog to the current framework version if possible."""
        raise NotImplementedError

    @abstractmethod
    def load_index(self, catalog: ICatalog) -> None:
        """Load the index from file or src. If a file and src exists routine tries to update the index."""
        raise NotImplementedError

    @abstractmethod
    def refresh_index(self, catalog: ICatalog) -> bool:
        """Routine to refresh the catalog index. Download or copy the index_file."""
        raise NotImplementedError

    @abstractmethod
    def migrate_solution_attrs(self, attrs) -> Dict[str, Any]:
        """Migrate the solution attributes to the current framework version."""
        raise NotImplementedError

    @abstractmethod
    def is_outdated_core_runner(
        self, solution_api_version: str, warn: bool = True
    ) -> bool:
        """Check if the solution API version is outdated."""
        raise NotImplementedError

    @abstractmethod
    def is_outdated_core(self, solution_api_version: str, warn: bool = True) -> bool:
        """Check if the core API version is outdated."""
        raise NotImplementedError

    @abstractmethod
    def get_outdated_runner_name_and_version(self) -> Tuple[str, str]:
        """Get the outdated runner name and version."""
        raise NotImplementedError

    @abstractmethod
    def is_outdated_solution_api(self, solution_api_version: str) -> bool:
        """Check if the current API version is available on conda-forge."""
        raise NotImplementedError
