import os
from pathlib import Path

from album.runner import album_logging
from album.runner.core.model.coordinates import Coordinates

from album.core.api.model.configuration import IConfiguration
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import (
    create_paths_recursively,
    force_remove,
    get_dict_from_json,
)

module_logger = album_logging.get_active_logger


class Configuration(IConfiguration):
    def __init__(self):
        self._is_setup = False
        self._base_cache_path = None
        self._micromamba_base_path = None
        self._tmp_path = None
        self._cache_path_envs = None
        self._catalog_collection_path = None
        self._installation_path = None
        self._lnk_path = None

    def base_cache_path(self):
        return self._base_cache_path

    def micromamba_base_path(self):
        return self._micromamba_base_path

    def installation_path(self):
        return self._installation_path

    def cache_path_download(self):
        return self._cache_path_download

    def tmp_path(self):
        return self._tmp_path

    def environments_path(self):
        return self._cache_path_envs

    def lnk_path(self):
        return self._lnk_path

    def is_setup(self):
        return self._is_setup

    def setup(self, base_cache_path=None):
        if self._is_setup:
            raise RuntimeError(
                "Configuration::setup was already called and should not be called twice."
            )
        self._is_setup = True
        # base root path where everything lives
        self._base_cache_path = Path(
            os.getenv("ALBUM_BASE_CACHE_PATH", DefaultValues.app_data_dir.value)
        )
        if base_cache_path:
            self._base_cache_path = Path(base_cache_path)

        self._micromamba_base_path = self._base_cache_path.joinpath(
            DefaultValues.micromamba_base_path.value
        )

        self._cache_path_download = self._base_cache_path.joinpath(
            DefaultValues.cache_path_download_prefix.value
        )
        self._cache_path_envs = self._base_cache_path.joinpath(
            DefaultValues.cache_path_envs_prefix.value
        )
        self._catalog_collection_path = self._base_cache_path.joinpath(
            DefaultValues.catalog_folder_prefix.value
        )
        self._installation_path = self._base_cache_path.joinpath(
            DefaultValues.installation_folder_prefix.value
        )
        self._tmp_path = self._base_cache_path.joinpath(
            DefaultValues.cache_path_tmp_prefix.value
        )
        self._lnk_path = self._base_cache_path.joinpath(
            DefaultValues.link_folder_prefix.value
        )
        self._empty_tmp()
        create_paths_recursively(
            [
                self._tmp_path,
                self._cache_path_download,
                self._cache_path_envs,
                self._catalog_collection_path,
                self._installation_path,
            ]
        )

    def get_solution_path_suffix(self, coordinates: Coordinates) -> Path:
        return Path("").joinpath(
            DefaultValues.catalog_solutions_prefix.value,
            coordinates.group(),
            coordinates.name(),
            coordinates.version(),
        )

    def get_solution_path_suffix_unversioned(self, coordinates: Coordinates) -> Path:
        return Path("").joinpath(
            DefaultValues.catalog_solutions_prefix.value,
            coordinates.group(),
            coordinates.name(),
        )

    def get_cache_path_catalog(self, catalog_name):
        return self._base_cache_path.joinpath(
            DefaultValues.catalog_folder_prefix.value, catalog_name
        )

    def get_catalog_collection_path(self):
        collection_db_path = Path(self._catalog_collection_path).joinpath(
            DefaultValues.catalog_collection_db_name.value
        )
        return collection_db_path

    def get_catalog_collection_meta_dict(self):
        """Returns the metadata of the collection as a dict."""
        catalog_collection_json = self.get_catalog_collection_meta_path()
        if not catalog_collection_json.exists():
            return None
        catalog_collection_dict = get_dict_from_json(catalog_collection_json)
        return catalog_collection_dict

    def get_catalog_collection_meta_path(self):
        return Path(self._catalog_collection_path).joinpath(
            DefaultValues.catalog_collection_json_name.value
        )

    def get_initial_catalogs(self):
        return {
            DefaultValues.default_catalog_name.value: DefaultValues.default_catalog_src.value
        }

    def get_initial_catalogs_branch_name(self):
        return {
            DefaultValues.default_catalog_name.value: DefaultValues.default_catalog_src_branch.value
        }

    def _empty_tmp(self):
        """Removes the content of the tmp folder"""
        # this should not be done since there could be links in tmp_user or tmp_internal which have to be resolved when deleting them
        # force_remove(self._cache_path_tmp_user)
        # force_remove(self._cache_path_tmp_internal)
        force_remove(self._tmp_path)
