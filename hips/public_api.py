import os
from pathlib import Path

import requests
from xdg import xdg_data_home, xdg_data_dirs

import utils.git_operations
from utils import hips_logging
from utils.git_operations import download_repository

module_logger = hips_logging.get_active_logger


def get_base_cache_path():
    """

    Returns: Path to local HIPS cache directory

    """
    return xdg_data_home().joinpath("hips")


def get_cache_path_hips(active_hips):
    """

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("solutions", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("solutions", "local", active_hips["group"], active_hips["name"], active_hips["version"])


def get_cache_path_app(active_hips):
    """

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of any apps belonging to a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("apps", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("apps", "local", active_hips["group"], active_hips["name"], active_hips["version"])


def get_cache_path_downloads(active_hips):
    """

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of any download files belonging to a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("downloads", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("downloads", "local", active_hips["group"], active_hips["name"], active_hips["version"])


def get_cache_path_catalog(catalog_id):
    """

    Args:
        catalog_id: The ID of the HIPS catalog

    Returns: Path to local cache of a catalog identified by the ID

    """
    return get_base_cache_path().joinpath("catalogs", catalog_id)


def download_if_not_exists(active_hips, url, file_name):
    """
    Downloads resource if not already cached and returns local resource path.

    Args:
        active_hips: The HIPS object the download belongs to
        url: The URL of the download
        file_name: The local filename of the download

    Returns: The path to the downloaded resource

    """
    download_dir = get_cache_path_downloads(active_hips)
    download_path = download_dir.joinpath(file_name)
    if download_path.exists():
        print(f"Found cache of {url}: {download_path}")
        return download_path
    if not download_dir.exists():
        download_dir.mkdir(parents=True)
    print(f"Downloading {url} to {download_path}")
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
    print(f"Extracting {in_tar} to {out_dir}")
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


def download_hips_catalog(active_hips):
    """Downloads the catalog specified in hips object.

    Args:
        active_hips:
            The hips object.

    Returns:
        The catalog repository as Repo object

    """
    catalog_url = active_hips['catalog']
    catalog_name = _extract_catalog_name(catalog_url)  # only the folder name of the local catalog git repo
    module_logger().debug("Donwload catalog %s to the name %s" % (catalog_url, catalog_name))

    #ToDo: replace name with id
    catalog_path = get_cache_path_catalog(catalog_name)

    repo = utils.git_operations.download_repository(catalog_url, catalog_path)

    return repo


def download_hips_repository(hips_object):
    """Downloads the repository specified in a hips object, returns repository_path on success.

    Additionally changes pythons working directory to the repository_path.

    Args:
        hips_object:
            The hips object.

    Returns:
        The directory of the git directory.

    """
    download_path = xdg_data_dirs()[0].joinpath(hips_object['name'])

    repo = download_repository(hips_object['git_repo'], download_path)

    repository_path = repo.working_tree_dir

    # set the repository path
    hips_object["_repository_path"] = repository_path

    # set python workdir
    os.chdir(repository_path)

    return repository_path
