from abc import ABCMeta, abstractmethod

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex


class IMigrationManager:
    """Interface handling the migration from Indices of different versions. Responsible for execution of SQL migration!

    Tries to always migrate the catalog index or collection index to the current framework version
    able to deal with the database.

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def migrate_collection_index(
        self, collection_index: ICollectionIndex, initial_version
    ):
        """Migrates a collection index database to the target version."""
        raise NotImplementedError

    @abstractmethod
    def migrate_catalog_collection_db(
        self, collection_index_path, curr_version, target_version
    ):
        """Migrates a given collection index to the target version."""
        raise NotImplementedError

    @abstractmethod
    def migrate_catalog_index_db(
        self, catalog_index_path, curr_version, target_version
    ):
        """Migrates the index of a given catalog to the current framework version if possible."""
        raise NotImplementedError

    @abstractmethod
    def load_index(self, catalog: ICatalog):
        """Loads the index from file or src. If a file and src exists routine tries to update the index."""
        raise NotImplementedError

    @abstractmethod
    def refresh_index(self, catalog: ICatalog) -> bool:
        """Routine to refresh the catalog index. Downloads or copies the index_file."""
        raise NotImplementedError

    @abstractmethod
    def migrate_solution_attrs(self, attrs):
        raise NotImplementedError
