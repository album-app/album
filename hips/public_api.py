from pathlib import Path

import requests
from xdg import xdg_data_home


def get_base_cache_path():
    """

    Returns: Path to local HIPS cache directory

    """
    return xdg_data_home().joinpath("hips")


def get_cache_path_hips(hips):
    """

    Args:
        hips: The HIPS object

    Returns: Path to local cache of a HIPS

    """
    if hasattr(hips, "doi"):
        return get_base_cache_path().joinpath("solutions", "doi", hips["doi"])
    else:
        return get_base_cache_path().joinpath("solutions", "local", hips["group"], hips["name"], hips["version"])


def get_cache_path_downloads(hips):
    """

    Args:
        hips: The HIPS object

    Returns: Path to local cache of any download files belonging to a HIPS

    """
    if hasattr(hips, "doi"):
        return get_base_cache_path().joinpath("downloads", "doi", hips["doi"])
    else:
        return get_base_cache_path().joinpath("downloads", "local", hips["group"], hips["name"], hips["version"])


def get_cache_path_catalog(catalog_id):
    """

    Args:
        catalog_id: The ID of the HIPS catalog

    Returns: Path to local cache of a catalog identified by the ID

    """
    return get_base_cache_path().joinpath("catalogs", catalog_id)


def download_if_not_exists(hips, url, file_name):
    """
    Downloads resource if not already cached and returns local resource path.

    Args:
        hips: The HIPS object the download belongs to
        url: The URL of the download
        file_name: The local filename of the download

    Returns: The path to the downloaded resource

    """
    download_dir = get_cache_path_downloads(hips)
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
