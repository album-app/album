import os
from pathlib import Path

import requests
from hips.core.model.configuration import HipsConfiguration

from hips.core.model import logging
from hips.core.utils.operations.git_operations import download_repository

module_logger = logging.get_active_logger


def download_if_not_exists(active_hips, url, file_name):
    """Downloads resource if not already cached and returns local resource path.

    Args:
        active_hips: The HIPS object the download belongs to
        url: The URL of the download
        file_name: The local filename of the download

    Returns: The path to the downloaded resource

    """
    configuration = HipsConfiguration()
    download_dir = configuration.get_cache_path_downloads(active_hips)
    download_path = download_dir.joinpath(file_name)
    if download_path.exists():
        module_logger().info(f"Found cache of {url}: {download_path}...")
        return download_path
    if not download_dir.exists():
        download_dir.mkdir(parents=True)
    module_logger().info(f"Downloading {url} to {download_path}...")
    downloaded_obj = requests.get(url)

    with open(str(download_path), "wb") as file:
        file.write(downloaded_obj.content)
    return download_path


# todo: write test
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
    module_logger().info(f"Extracting {in_tar} to {out_dir}...")
    my_tar = tarfile.open(in_tar)
    my_tar.extractall(out_dir)
    my_tar.close()


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


# todo: write test
def install_package(module, environment_name, version=None):
    """Installs a package in an environment.

    Args:
        module:
            The module name or a git like link. (e.g. "git+..." pip installation)
        environment_name:
            The name of the environment.
        version:
            The version of the package. If none, give, current latest is taken.

    """
    from hips.core import pip_install
    pip_install(module, version=version, environment_name=environment_name)
