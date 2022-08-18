import os
import platform
from enum import Enum
from pathlib import Path

import album.core


class DefaultValues(Enum):
    """Add an entry here to initialize default attributes for a album framework installation instance."""

    album_cite_doi = "arXiv:2110.00601"  # album DOI
    album_cite_text = "Albrecht, Schmidt, Harrington. Album: a framework for scientific data processing with software solutions of heterogeneous tools."  # album text
    album_cite_url = "https://album.solutions"  # album url

    # runner
    runner_api_packet_version = "0.5.1"  # set to None to use with url
    runner_api_packet_name = "album-runner"  # can also point to zip/url like: https://gitlab.com/album-app/album-runner/-/archive/main/album-runner-main.zip
    runner_pip_version = "pip=21.0"
    first_runner_conda_version = "0.5.1"
    default_solution_python_version = "3.9"

    # templates
    catalog_template_url = "https://gitlab.com/album-app/catalogs/templates"  # base URL of available catalog templates

    # deployment & cloning
    catalog_git_user = "album"  # username used for initial push to a new catalog
    catalog_git_email = (
        album.core.__email__
    )  # email used for initial push to a new catalog

    # catalog
    cache_catalog_name = (
        "cache_catalog"  # the default name of the cache catalog (always configured)
    )
    _catalog_url = "https://gitlab.com/album-app/catalogs/default"
    _catalog_branch = "main"
    default_catalog_src = os.getenv(
        "ALBUM_DEFAULT_CATALOG", _catalog_url
    )  # default catalog, either catalog_url or env. variable
    default_catalog_src_branch = os.getenv(
        'ALBUM_DEFAULT_CATALOG_BRANCH', _catalog_branch
    )                                                                      # default catalog branch either _catalog_branch or env. variable
    default_catalog_name = "default"                                       # default catalog, either catalog_url or env. variable
    catalog_collection_name = 'album_collection'                           # the default name of the Collection
    catalog_collection_db_name = 'catalog_collection.db'                   # the default name of the Collection DB
    catalog_collection_json_name = 'catalog_collection.json'               # the default name of the Collection JSON
    catalog_collection_db_version = '0.1.0'                                # the version of the collection database created by this album version
    catalog_index_file_name = 'album_catalog_index.db'                     # the default index file name of the catalog_index
    catalog_index_metafile_json = 'album_catalog_index.json'               # the default meta file name of the catalog_index
    catalog_index_db_version = '0.1.0'                                     # the version of the catalog database created by this album version
    catalog_solution_list_file_name = 'album_solution_list.json'           # the default file name for exporting the list of solutions of a catalog
    catalog_folder_prefix = 'catalogs'                                     # base folder prefix where all not local catalogs live
    installation_folder_prefix = "installations"                           # base folder prefix where installations live
    cache_path_tmp_prefix = "tmp"                                          # base folder prefix where solution unspecific internal temporary files live
    link_folder_prefix = 'lnk'                                             # base folder prefix where all internal link destinations live
    catalog_solutions_prefix = "solutions"                                 # base folder prefix where solutions live
    cache_path_download_prefix = "downloads"                               # base folder prefix where downloads live
    cache_path_envs_prefix = "envs"                                        # base folder prefix where environments live in

    # solutions
    solution_default_name = (
        "solution.py"  # default name how solution.py files are called
    )
    solution_yml_default_name = "solution.yml"  # default name of the solution.yml file
    solution_zip_default_name = "solution.zip"  # default name of the solution.zip file
    changelog_default_name = "CHANGELOG.md"  # default name of the changelog file

    # lnk folder prefixes
    lnk_package_prefix = (
        "pck"  # short name of the folder linked to from the catalogs directory
    )
    lnk_env_prefix = (
        "env"  # short name of the folder linked to from the environments directory
    )
    lnk_solution_prefix = (
        "inst"  # short name of the folder linked to from the installations
    )

    # solution specific files living in the installations folder
    solution_app_prefix = "app"  # solution specific app files
    solution_data_prefix = "data"  # solution specific data files
    solution_internal_cache_prefix = (
        "icache"  # solution specific album internal cache files
    )
    solution_user_cache_prefix = (
        "ucache"  # solution specific user cache files, accessible via runner API
    )

    # environment
    default_environment = (
        "album"  # default environment name the album framework operates from
    )

    # album
    app_data_dir = Path.home().joinpath(".album")  # base data path

    # conda
    conda_default_executable = "conda"  # default conda executable
    conda_path = os.getenv(
        "ALBUM_CONDA_PATH", conda_default_executable
    )  # default conda path, either env. var or conda

    # micromamba
    # These default executable cannot be used for environment activation!
    micromamba_default_windows_executable = str(
        Path(str(app_data_dir)).joinpath("micromamba", "Library", "bin",
                                         "micromamba.exe"))  # default micromamba executable on windows
    micromamba_default_unix_executable = str(
        Path(str(app_data_dir)).joinpath("micromamba", "bin",
                                         "micromamba"))  # default micromamba executable on windows
    if platform.system() == "Windows":
        micromamba_path = os.getenv("ALBUM_CONDA_PATH", micromamba_default_windows_executable)
    else:
        micromamba_path = os.getenv("ALBUM_CONDA_PATH", micromamba_default_unix_executable)

    # events
    before_run_event_name = "before-run"
    after_run_event_name = "after-run"

    # server
    server_port = 5476  # default port used to launch server
    server_host = "127.0.0.1"  # default host used to launch server. Set to 0.0.0.0 when used in docker
