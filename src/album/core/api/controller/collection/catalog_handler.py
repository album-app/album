from abc import ABCMeta, abstractmethod
from typing import Optional, List, Dict

from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_updates import ICatalogUpdates


class ICatalogHandler:
    __metaclass__ = ABCMeta

    @abstractmethod
    def create_cache_catalog(self):
        """Creates the local catalog on the disk from the available initial catalogs.

        Does not contain a DB file. Used only when album starts the first time.

        """
        raise NotImplementedError

    @abstractmethod
    def add_initial_catalogs(self):
        """Adds the initial catalogs to the catalog_collection.

        Copies/downloads them from their src to their local cache. (Except local_catalog)

        """
        raise NotImplementedError

    @abstractmethod
    def add_by_src(self, source, branch_name="main") -> ICatalog:
        """Adds a catalog. Creates them from their src. (Git, network-drive, folder outside cache, etc.)"""
        raise NotImplementedError

    @abstractmethod
    def _add_to_index(self, catalog: ICatalog) -> int:
        """Adds a catalog to the collection index.

        Args:
            catalog: The catalog object

        Returns:
            The database ID of the catalog.

        """
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, catalog_id) -> ICatalog:
        """Looks up a catalog by its id and returns it."""
        raise NotImplementedError

    @abstractmethod
    def get_by_src(self, src) -> ICatalog:
        """Returns the catalog object of a given url if configured."""
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, name) -> ICatalog:
        """Looks up a catalog by its id and returns it."""
        raise NotImplementedError

    @abstractmethod
    def get_by_path(self, path) -> ICatalog:
        """Looks up a catalog by its id and returns it."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> List[ICatalog]:
        """Creates the catalog objects from the catalogs specified in the configuration."""
        raise NotImplementedError

    @abstractmethod
    def get_cache_catalog(self) -> ICatalog:
        """Returns the first cache catalog in the configuration (Reads db table from top)."""
        raise NotImplementedError

    @abstractmethod
    def create_new_metadata(self, local_path, name, catalog_type):
        """Creates a new catalog on the disk."""
        raise NotImplementedError

    @abstractmethod
    def update_by_name(self, catalog_name) -> bool:
        """Updates a catalog by its name."""
        raise NotImplementedError

    @abstractmethod
    def update_all(self) -> List[bool]:
        """Updates all available catalogs"""
        raise NotImplementedError

    @abstractmethod
    def update_any(self, catalog_name=None):
        """Updates either all catalogs or one by its name."""
        raise NotImplementedError

    @abstractmethod
    def update_collection(
        self, catalog_name=None, dry_run: bool = False, override: bool = False
    ) -> Dict[str, ICatalogUpdates]:
        """Includes all new changes from a given catalog (or all catalogs) in the catalog_collection."""
        raise NotImplementedError

    @abstractmethod
    def remove_from_collection_by_path(self, path) -> Optional[ICatalog]:
        """Removes a catalog given by its path from the catalog_collection.

        Thereby deleting all its entries from the collection.

        """
        raise NotImplementedError

    @abstractmethod
    def remove_from_collection_by_name(self, name) -> Optional[ICatalog]:
        """Removes a catalog given its name from the catalog_collection."""
        raise NotImplementedError

    @abstractmethod
    def remove_from_collection_by_src(self, src) -> Optional[ICatalog]:
        """Removes a catalog given its src from the catalog_collection."""
        raise NotImplementedError

    @abstractmethod
    def get_installed_solutions(self, catalog: ICatalog) -> list:
        """Get all installed solutions of a catalog"""
        raise NotImplementedError

    @abstractmethod
    def get_all_as_dict(self) -> dict:
        """Get all catalogs as dictionary."""
        raise NotImplementedError

    @abstractmethod
    def set_version(self, catalog: ICatalog):
        raise NotImplementedError
