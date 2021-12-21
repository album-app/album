import os
from enum import Enum
from pathlib import Path

from appdirs import user_data_dir, user_cache_dir, user_config_dir


class DefaultValues(Enum):
    """Add an entry here to initialize default attributes for a album framework installation instance."""

    # runner
    runner_api_packet_version = '0.2.1'      # set to None to use with url
    runner_api_packet_name = 'album-runner'  # can also point to zip/url like: https://gitlab.com/album-app/album-runner/-/archive/main/album-runner-main.zip

    # templates
    catalog_template_url = 'https://gitlab.com/album-app/catalogs/templates'  # base URL of available catalog templates

    # catalog
    local_catalog_name = 'catalog_local'                                   # the default name of the local catalog (always configured)
    _catalog_url = 'https://gitlab.com/album-app/catalogs/default'
    _catalog_branch = "main"
    default_catalog_src = os.getenv('ALBUM_DEFAULT_CATALOG', _catalog_url) # default catalog, either catalog_url or env. variable
    default_catalog_src_branch = os.getenv(
        'ALBUM_DEFAULT_CATALOG_BRANCH', _catalog_branch
    )                                                                      # default catalog branch either _catalog_branch or env. variable
    default_catalog_name = "default"                                       # default catalog, either catalog_url or env. variable
    catalog_collection_name = 'album_collection'                           # the default name of the Collection
    catalog_collection_db_name = 'catalog_collection.db'                   # the default name of the Collection DB
    catalog_collection_json_name = 'catalog_collection.json'               # the default name of the Collection JSON
    catalog_index_file_name = 'album_catalog_index.db'                     # the default index file name of the catalog_index
    catalog_index_metafile_json = 'album_catalog_index.json'               # the default meta file name of the catalog_index
    catalog_solution_list_file_name = 'album_solution_list.json'           # the default file name for exporting the list of solutions of a catalog
    catalog_folder_prefix = 'catalogs'                                     # base folder prefix where all not local catalogs live
    cache_path_solution_prefix = "solutions"                               # base folder prefix where solutions live
    cache_path_app_prefix = "apps"                                         # base folder prefix where app solutions live
    cache_path_download_prefix = "downloads"                               # base folder prefix where downloads live
    cache_path_tmp_prefix = "tmp"                                          # base folder prefix where temporary files live
    cache_path_envs_prefix = "envs"                                        # base folder prefix where environments live in
    solution_default_name = "solution.py"                                  # default name how solution.py files are called

    # environment
    default_environment = "album"            # default environment name the album framework operates from

    # album
    app_data_dir = Path(user_data_dir("album"))      # base data path
    app_cache_dir = Path(user_cache_dir("album"))    # base cache path
    app_config_dir = Path(user_config_dir("album"))  # base configuration path

    # conda
    conda_default_executable = "conda"                                   # default conda executable
    conda_path = os.getenv('ALBUM_CONDA_PATH', conda_default_executable)  # default conda path, either env. var or conda

    # server
    server_port = 5476  # default port used to launch server
    server_host = "127.0.0.1"  # default host used to launch server. Set to 0.0.0.0 when used in docker
