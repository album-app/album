import os
from enum import Enum
from pathlib import Path

from appdirs import user_data_dir, user_cache_dir, user_config_dir


class HipsDefaultValues(Enum):
    """Add an entry here to initialize default attributes for a hips framework installation instance."""

    # deployment
    catalog_url = 'https://gitlab.com/ida-mdc/hips-catalog.git'  # default deployment url
    catalog = os.getenv('HIPS_DEFAULT_CATALOG', catalog_url)     # default catalog, either catalog_url or env. variable
    catalog_yaml_prefix = "catalog"                              # base folder name where yaml files of solutions
                                                                 # are stored in a catalog.

    # catalog
    local_catalog_name = 'catalog_local'              # the default name of the local catalog (always configured)
    catalog_index_file_name = 'catalog_index'         # the default index file name of the catalog_index
    cache_path_solution_prefix = "solutions"          # base folder name where solutions live
    cache_path_doi_solution_prefix = "doi_solutions"  # base folder name where doi solutions live
    cache_path_app_prefix = "apps"                    # base folder name where app solutions live
    cache_path_download_prefix = "downloads"          # base folder name where downloads live
    solution_default_name = "solution.py"             # default name how solution.py files are called

    # environment
    default_environment = "hips"            # default environment name the hips framework operates from

    # hips
    hips_config_file_name = '.hips-config'          # file name of the hips configuration file
    app_data_dir = Path(user_data_dir("hips"))      # base data path
    app_cache_dir = Path(user_cache_dir("hips"))    # base cache path
    app_config_dir = Path(user_config_dir("hips"))  # base configuration path

    # conda
    conda_default_executable = "conda"                                   # default conda executable
    conda_path = os.getenv('HIPS_CONDA_PATH', conda_default_executable)  # default conda path, either env. var or conda
