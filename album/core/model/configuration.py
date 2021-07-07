import os
import sys
from pathlib import Path

from album.core.concept.singleton import Singleton
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import create_paths_recursively, force_remove
from album_runner import logging

module_logger = logging.get_active_logger


class Configuration(metaclass=Singleton):
    """Configuration of the album framework installation instance.

    This class manages the cache paths of the album framework installation instance.

    Attributes:
         base_cache_path:
            The base path all other cache folder have as parent folder.
         configuration_file_path:
            The path to the configuration file holding the catalogs.
         conda_executable:
            The conda executable. Either a full path to a conda executable/binary or a command
        cache_path_solution:
            Path for everything a solution needs. Holds the environment cache path. Catalog independent!
            NOT the installation folder though! Installation folder is always in the catalog it lives in!
        cache_path_app:
            Path for app solutions. Catalog independent!
        cache_path_download:
            Path for downloads a solution makes. Catalog independent!
        cache_path_tmp:
            Paths for temporary files!

    """

    def __init__(self, base_cache_path=None, configuration_file_path=None):
        if base_cache_path:
            self.base_cache_path = Path(base_cache_path)
        else:
            self.base_cache_path = DefaultValues.app_data_dir.value

        if configuration_file_path:
            self.configuration_file_path = Path(configuration_file_path)
        else:
            self.configuration_file_path = DefaultValues.app_config_dir.value.joinpath(
                DefaultValues.config_file_name.value)

        conda_path = DefaultValues.conda_path.value
        if conda_path is not DefaultValues.conda_default_executable.value:
            self.conda_executable = self.__build_conda_executable(conda_path)
        else:
            self.conda_executable = conda_path

    @staticmethod
    def __build_conda_executable(conda_path):
        operation_system = sys.platform
        if operation_system == 'linux' or operation_system == 'darwin':
            return str(Path(conda_path).joinpath("bin").joinpath("conda"))
        else:
            return str(Path(conda_path).joinpath("Scripts").joinpath("conda.exe"))

    @property
    def base_cache_path(self):
        return self._base_cache_path

    @base_cache_path.setter
    def base_cache_path(self, value):
        self._base_cache_path = Path(value)
        self.cache_path_solution = self.base_cache_path.joinpath(DefaultValues.cache_path_solution_prefix.value)
        self.cache_path_app = self.base_cache_path.joinpath(DefaultValues.cache_path_app_prefix.value)
        self.cache_path_download = self.base_cache_path.joinpath(DefaultValues.cache_path_download_prefix.value)
        self.cache_path_tmp = self.base_cache_path.joinpath(DefaultValues.cache_path_tmp_prefix.value)
        create_paths_recursively(
            [self.cache_path_solution, self.cache_path_app, self.cache_path_download, self.cache_path_tmp]
        )

    @property
    def conda_executable(self):
        return self._conda_executable

    @conda_executable.setter
    def conda_executable(self, value):
        self._conda_executable = value

    @staticmethod
    def get_solution_path_suffix(g, n, v):
        """Returns the suffix path for an album giving its group, name and version"""
        return Path("").joinpath(DefaultValues.cache_path_solution_prefix.value, g, n, v)

    @staticmethod
    def get_doi_solution_path_suffix(doi):
        """Returns the suffix path for an album giving its doi"""
        return Path("").joinpath(DefaultValues.cache_path_doi_solution_prefix.value, doi)

    def get_cache_path_catalog(self, catalog_id):
        """Get the cache path to the catalog with a certain ID. Catalog independent!

        Args:
            catalog_id: The ID of the album catalog

        Returns: Path to local cache of a catalog identified by the ID

        """
        return self.base_cache_path.joinpath(DefaultValues.catalog_folder_prefix.value, catalog_id)

    def get_default_configuration(self):
        """Creates the default album configuration dict which will be written in the album configuration yaml file."""
        config_file_dict = {
            "catalogs": self.get_default_catalog_configuration(),
            # here more defaults can follow
        }

        return config_file_dict

    def get_default_catalog_configuration(self):
        """Returns the default catalog configuration."""
        return [
            str(self.get_cache_path_catalog(DefaultValues.local_catalog_name.value)),
            DefaultValues.catalog.value,
        ]

    @staticmethod
    def extract_catalog_name(catalog_repo):
        """Extracts a basename from a repository URL.

        Args:
            catalog_repo:
                The repository URL or ssh string of the catalog.

        Returns:
            The basename of the repository

        """
        name, _ = os.path.splitext(os.path.basename(catalog_repo))
        return name

    def empty_tmp(self):
        """Removes the content of the tmp folder"""
        force_remove(self.cache_path_tmp)
