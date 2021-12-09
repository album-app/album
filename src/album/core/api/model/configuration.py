from abc import ABCMeta, abstractmethod
from pathlib import Path

from album.runner.core.api.model.coordinates import ICoordinates


class IConfiguration:
    """Configuration of the album framework installation instance.

    This interface manages the cache paths of the album framework installation instance.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def base_cache_path(self):
        """The base path all other cache folder have as parent folder."""
        raise NotImplementedError

    @abstractmethod
    def conda_executable(self):
        """The conda executable. Either a full path to a conda executable/binary or a command"""
        raise NotImplementedError

    @abstractmethod
    def cache_path_app(self):
        """Path for app solutions."""
        raise NotImplementedError

    @abstractmethod
    def cache_path_download(self):
        """Path for downloads a solution makes."""
        raise NotImplementedError

    @abstractmethod
    def cache_path_tmp_internal(self):
        """Path for solution specific temporary files of album."""
        raise NotImplementedError

    @abstractmethod
    def cache_path_tmp_user(self):
        """Path for solution specific temporary files of the user."""
        raise NotImplementedError

    @abstractmethod
    def cache_path_envs(self):
        """Path for solution specific environment files of album."""
        raise NotImplementedError

    @abstractmethod
    def is_setup(self):
        """If configuration was already initialized."""
        raise NotImplementedError

    @abstractmethod
    def setup(self, base_cache_path=None):
        raise NotImplementedError

    @abstractmethod
    def get_solution_path_suffix(self, coordinates: ICoordinates) -> Path:
        """Returns the suffix path for a solution giving its group, name and version"""
        raise NotImplementedError

    @abstractmethod
    def get_cache_path_catalog(self, catalog_name):
        """Get the cache path to the catalog with a certain ID. Catalog independent!

        Args:
            catalog_name: The ID of the album catalog

        Returns: Path to local cache of a catalog identified by the ID

        """
        raise NotImplementedError

    @abstractmethod
    def get_catalog_collection_path(self):
        """Returns the path of the collection database file."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_collection_meta_dict(self):
        """Returns the metadata of the collection as a dict."""
        raise NotImplementedError

    @abstractmethod
    def get_catalog_collection_meta_path(self):
        raise NotImplementedError

    @abstractmethod
    def get_initial_catalogs(self):
        """Returns the catalogs initially added to the collection as a dict."""
        raise NotImplementedError

    @abstractmethod
    def get_initial_catalogs_branch_name(self):
        """Returns the default catalogs branches to use."""
        raise NotImplementedError
