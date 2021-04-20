import os
from pathlib import Path

import requests


from xdg import xdg_data_home, xdg_config_home

from hips.hips_base import HipsDefaultValues
from hips_utils import hips_logging, subcommand
from hips_utils.operations.git_operations import download_repository

module_logger = hips_logging.get_active_logger


# todo: move to smth else and wirte a wrapper here. Causing circular dependency import errors!
def get_configuration_file_path():
    """Get the path to the HIPS runtime configuration file."""
    return xdg_config_home().joinpath(HipsDefaultValues.hips_config_file_name.value)


# todo: move to smth else and wirte a wrapper here. Causing circular dependency import errors!
def get_base_cache_path():
    """Get path to local HIPS cache directory"""
    return xdg_data_home().joinpath("hips")


# todo: move to smth else and wirte a wrapper here. Causing circular dependency import errors!
def get_cache_path_hips(active_hips):
    """Get the cache path of the active hips

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("solutions", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("solutions", "local", active_hips["group"], active_hips["name"], active_hips["version"])


# todo: move to smth else and wirte a wrapper here. Causing circular dependency import errors!
def get_cache_path_app(active_hips):
    """Get the app cache path of the active hips

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of any apps belonging to a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("apps", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("apps", "local", active_hips["group"], active_hips["name"], active_hips["version"])


# todo: move to smth else and wirte a wrapper here. Causing circular dependency import errors!
def get_cache_path_downloads(active_hips):
    """Get the cache path of anything a hips downloads.

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of any download files belonging to a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("downloads", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("downloads", "local", active_hips["group"], active_hips["name"], active_hips["version"])


# todo: move to smth else and wirte a wrapper here. Causing circular dependency import errors!
def get_cache_path_catalog(catalog_id):
    """Get the cache path to the catalog with a certain ID.

    Args:
        catalog_id: The ID of the HIPS catalog

    Returns: Path to local cache of a catalog identified by the ID

    """
    return get_base_cache_path().joinpath("catalogs", catalog_id)


def download_if_not_exists(active_hips, url, file_name):
    """Downloads resource if not already cached and returns local resource path.

    Args:
        active_hips: The HIPS object the download belongs to
        url: The URL of the download
        file_name: The local filename of the download

    Returns: The path to the downloaded resource

    """
    download_dir = get_cache_path_downloads(active_hips)
    download_path = download_dir.joinpath(file_name)
    if download_path.exists():
        module_logger().info(f"Found cache of {url}: {download_path}")
        return download_path
    if not download_dir.exists():
        download_dir.mkdir(parents=True)
    module_logger().info(f"Downloading {url} to {download_path}")
    downloaded_obj = requests.get(url)

    with open(str(download_path), "wb") as file:
        file.write(downloaded_obj.content)
    return download_path


def extract_tar(in_tar, out_dir):
    """

    Args:
        out_dir: Directory where the TAR file should be extracted to
        in_tar: TAR file to be extracted
    """
    import tarfile
    out_path = Path(out_dir)
    if not out_path.exists():
        out_path.mkdir(parents=True)
    module_logger().info(f"Extracting {in_tar} to {out_dir}")
    my_tar = tarfile.open(in_tar)
    my_tar.extractall(out_dir)
    my_tar.close()


def _extract_catalog_name(catalog_repo):
    """Extracts a basename from a repository URL.

    Args:
        catalog_repo:
            The repository URL or ssh string of the catalog.

    Returns:
        The basename of the repository

    """
    name, _ = os.path.splitext(os.path.basename(catalog_repo))
    return name


def download_hips_repository(active_hips):
    """Downloads the repository specified in a hips object, returns repository_path on success.

    Additionally changes pythons working directory to the repository_path.

    Args:
        active_hips:
            The hips object.

    Returns:
        The directory of the git directory.

    """
    download_path = get_cache_path_hips(active_hips).joinpath(active_hips["name"])

    repo = download_repository(active_hips['git_repo'], download_path)

    repository_path = repo.working_tree_dir

    # set the repository path
    active_hips["_repository_path"] = repository_path

    # set python workdir
    os.chdir(repository_path)

    return repository_path


# ToDo: write tests
def chdir_repository(active_hips):
    repo_path = get_cache_path_hips(active_hips).joinpath(active_hips["name"])

    # assumes repo is up to date!
    if repo_path.joinpath(".git").exists():
        os.chdir(str(repo_path))
    else:
        raise FileNotFoundError("Could not identify %s as repository. Aborting..." % repo_path)


def install_package(module, environment_name, version=None):
    from hips_utils.environment import pip_install
    pip_install(module, version=version, environment_name=environment_name)


def run_as_executable(cmd, args):
    from hips import get_active_hips
    from hips_utils.environment import set_environment_name, set_environment_path

    active_hips = get_active_hips()
    set_environment_name(active_hips)
    environment_path = Path(set_environment_path(active_hips))

    executable_path = environment_path.joinpath("bin", cmd)
    cmd = [
        str(executable_path)
    ] + args

    subcommand.run(cmd)
