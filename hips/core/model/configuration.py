import os
import sys
from pathlib import Path

from hips.core.concept.singleton import Singleton
from hips.core.model.default_values import HipsDefaultValues
from hips_runner import logging

module_logger = logging.get_active_logger


class HipsConfiguration(metaclass=Singleton):
    """Configuration of the HIPS framework installation instance.

    This class manages the cache paths of the HIPS framework installation instance.

    Attributes:
         base_cache_path:
            The base path all other cache folder have as parent folder.
         configuration_file_path:
            The path to the configuration file holding the catalogs.
         conda_executable:
            The conda executable. Either a full path to a conda executable/binary or a command

    """

    def __init__(self, base_cache_path=None, configuration_file_path=None):
        if base_cache_path:
            self.base_cache_path = Path(base_cache_path)
        else:
            self.base_cache_path = HipsDefaultValues.app_data_dir.value

        if configuration_file_path:
            self.configuration_file_path = Path(configuration_file_path)
        else:
            self.configuration_file_path = HipsDefaultValues.app_config_dir.value.joinpath(
                HipsDefaultValues.hips_config_file_name.value)

        conda_path = HipsDefaultValues.conda_path.value
        if conda_path is not HipsDefaultValues.conda_default_executable.value:
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
        self._base_cache_path = value
        self.cache_path_solution = self.base_cache_path.joinpath(HipsDefaultValues.cache_path_solution_prefix.value)
        self.cache_path_app = self.base_cache_path.joinpath(HipsDefaultValues.cache_path_app_prefix.value)
        self.cache_path_download = self.base_cache_path.joinpath(HipsDefaultValues.cache_path_download_prefix.value)

    @property
    def conda_executable(self):
        return self._conda_executable

    @conda_executable.setter
    def conda_executable(self, value):
        self._conda_executable = value

    def get_cache_path_hips(self, active_hips):
        """Get the cache path of the active hips

        Args:
            active_hips: The HIPS object

        Returns: Path to local cache of a HIPS

        """
        if hasattr(active_hips, "doi"):
            return self.cache_path_solution.joinpath("doi", active_hips["doi"])
        else:
            return self.cache_path_solution.joinpath("local", active_hips["group"], active_hips["name"],
                                                     active_hips["version"])

    def get_cache_path_app(self, active_hips):
        """Get the app cache path of the active hips

        Args:
            active_hips: The HIPS object

        Returns: Path to local cache of any apps belonging to a HIPS

        """
        if hasattr(active_hips, "doi"):
            return self.cache_path_app.joinpath("doi", active_hips["doi"])
        else:
            return self.cache_path_app.joinpath("local", active_hips["group"], active_hips["name"],
                                                active_hips["version"])

    def get_cache_path_downloads(self, active_hips):
        """Get the cache path of anything a hips downloads.

        Args:
            active_hips: The HIPS object

        Returns: Path to local cache of any download files belonging to a HIPS

        """
        if hasattr(active_hips, "doi"):
            return self.cache_path_download.joinpath("doi", active_hips["doi"])
        else:
            return self.cache_path_download.joinpath("local", active_hips["group"], active_hips["name"],
                                                     active_hips["version"])

    def get_cache_path_catalog(self, catalog_id):
        """Get the cache path to the catalog with a certain ID.

        Args:
            catalog_id: The ID of the HIPS catalog

        Returns: Path to local cache of a catalog identified by the ID

        """
        return self.base_cache_path.joinpath("catalogs", catalog_id)

    def get_default_hips_configuration(self):
        """Creates the default hips configuration dict which will be written in the hips configuration yaml file."""
        config_file_dict = {
            "catalogs": self.get_default_catalog_configuration(),
            # here more defaults can follow
        }

        return config_file_dict

    def get_default_catalog_configuration(self):
        """Returns the default catalog configuration."""
        return [
            str(self.get_cache_path_catalog(HipsDefaultValues.local_catalog_name.value)),
            HipsDefaultValues.catalog.value,
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
