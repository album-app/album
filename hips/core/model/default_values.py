import os
from enum import Enum
from pathlib import Path

from appdirs import user_data_dir, user_cache_dir, user_config_dir


class HipsDefaultValues(Enum):
    """Add a entry here to initialize default attributes for a hips object.

     Takes the Enum name as attribute name and the Enum value as default value.
     """
    catalog = os.getenv('HIPS_DEFAULT_CATALOG', 'https://gitlab.com/ida-mdc/hips-catalog.git')
    local_catalog_name = 'catalog_local'
    catalog_index_file_name = 'catalog_index'
    hips_config_file_name = '.hips-config'
    cache_path_solution_prefix = "solutions"
    cache_path_app_prefix = "apps"
    cache_path_download_prefix = "downloads"
    default_environment = "hips"

    app_data_dir = Path(user_data_dir("hips"))
    app_cache_dir = Path(user_cache_dir("hips"))
    app_config_dir = Path(user_config_dir("hips"))
