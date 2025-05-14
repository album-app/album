"""Configuration of the album framework installation instance."""
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union

from album.runner.core.api.model.coordinates import ICoordinates


class IConfiguration:
    """Configuration of the album framework installation instance.

    This interface manages the cache paths of the album framework installation instance.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def base_cache_path(self) -> Path:
        """Get the base path all other cache folder have as parent folder."""
        raise NotImplementedError

    @abstractmethod
    def cache_path_download(self) -> Path:
        """Get the path for solution unspecific downloads."""
        raise NotImplementedError

    @abstractmethod
    def tmp_path(self) -> Path:
        """Get the path for solution unspecific temporary files of album."""
        raise NotImplementedError

    @abstractmethod
    def environments_path(self) -> Path:
        """Get the path for solution environments."""
        raise NotImplementedError

    @abstractmethod
    def installation_path(self) -> Path:
        """Get the path for solution installation files."""
        raise NotImplementedError

    @abstractmethod
    def lnk_path(self) -> Path:
        """Path for targets of internal links, used to shorten paths (thank you Windows)."""
        raise NotImplementedError

    @abstractmethod
    def shared_resources_path(self) -> Path:
        """Path for shared resources."""
        raise NotImplementedError

    @abstractmethod
    def is_setup(self) -> bool:
        """Check if configuration was already performed."""
        raise NotImplementedError

    @abstractmethod
    def setup(self, base_cache_path: Union[None, str, Path] = None) -> None:
        """Set up the configuration."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_path_suffix(self, coordinates: ICoordinates) -> Path:
        """Return the suffix path for a solution giving its group, name and version."""
        raise NotImplementedError

    @abstractmethod
    def get_solution_path_suffix_unversioned(self, coordinates: ICoordinates) -> Path:
        """Return the suffix path for a solution giving its group and name."""
        raise NotImplementedError

    @abstractmethod
    def get_cache_path_catalog(self, catalog_name: str) -> Path:
        """Get the cache path to the catalog with a certain ID.

         Catalog independent cache path!

        Args:
            catalog_name: The ID of the album catalog

        Returns: Path to local cache of a catalog identified by the ID

        """
        raise NotImplementedError

    @abstractmethod
    def get_catalog_collection_path(self) -> Path:
        """Return the path of the collection database file."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_collection_meta_dict(self) -> Optional[Dict[str, Any]]:
        """Return the metadata of the collection as a dict."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_collection_meta_path(self) -> Path:
        """Return the path of the collection metadata file."""
        raise NotImplementedError

    @abstractmethod
    def get_initial_catalogs(self) -> Dict[str, str]:
        """Return the catalogs initially added to the collection as a dict."""
        raise NotImplementedError

    @abstractmethod
    def get_initial_catalogs_branch_name(self) -> Dict[str, str]:
        """Return the default catalogs branches to use."""
        raise NotImplementedError
