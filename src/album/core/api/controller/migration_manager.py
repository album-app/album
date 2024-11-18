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
    def is_solution_api_outdated(
        self, solution_api_version: str, warn: bool = True
    ) -> bool:
        """Check if the given solution API version is smaller than the first known solution_api_version of this installation."""  # noqa: E501
        raise NotImplementedError

    @abstractmethod
    def is_core_api_outdated(
        self, solution_api_version: str, warn: bool = True
    ) -> bool:
        """Check if the given solution API version is higher than the solution_api_version of this installation."""
        raise NotImplementedError

    @abstractmethod
    def is_migration_needed_solution_api(self, solution_api_version: str) -> bool:
        """Check if the given solution API version needs the migration routine when scripts are executed."""
        raise NotImplementedError

    @abstractmethod
    def get_conda_available_outdated_runner_name_and_version(self) -> Tuple[str, str]:
        """Get the outdated runner name and version."""
        raise NotImplementedError
