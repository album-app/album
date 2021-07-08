import os
from enum import Enum
from pathlib import Path

from appdirs import user_data_dir, user_cache_dir, user_config_dir


class DefaultValues(Enum):
    """Add an entry here to initialize default attributes for a album framework installation instance."""

    # deployment
    catalog_url = 'https://gitlab.com/album-app/capture-knowledge'  # default deployment url
    runner_rul = 'https://gitlab.com/album-app/album-runner'        # default runner url
    catalog = os.getenv('ALBUM_DEFAULT_CATALOG', catalog_url)     # default catalog, either catalog_url or env. variable
    catalog_yaml_prefix = "catalog"                              # base folder name where yaml files of solutions
                                                                 # are stored in a catalog.

    # catalog
    local_catalog_name = 'catalog_local'              # the default name of the local catalog (always configured)
    catalog_index_file_name = 'catalog_index'         # the default index file name of the catalog_index
    catalog_folder_prefix = 'catalogs'                # base folder prefix where all not local catalogs live
    cache_path_solution_prefix = "solutions"          # base folder prefix where solutions live
    cache_path_doi_solution_prefix = "doi_solutions"  # base folder prefix where doi solutions live
    cache_path_app_prefix = "apps"                    # base folder prefix where app solutions live
    cache_path_download_prefix = "downloads"          # base folder prefix where downloads live
    cache_path_tmp_prefix = "tmp"                     # base folder prefix where temporary files live
    solution_default_name = "solution.py"             # default name how solution.py files are called

    # environment
    default_environment = "album"            # default environment name the album framework operates from

    # album
    config_file_name = '.album-config'               # file name of the album configuration file
    app_data_dir = Path(user_data_dir("album"))      # base data path
    app_cache_dir = Path(user_cache_dir("album"))    # base cache path
    app_config_dir = Path(user_config_dir("album"))  # base configuration path

    # conda
    conda_default_executable = "conda"                                   # default conda executable
    conda_path = os.getenv('ALBUM_CONDA_PATH', conda_default_executable)  # default conda path, either env. var or conda
