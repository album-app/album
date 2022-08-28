import errno
import os
import re
import sys
from pathlib import Path
from typing import Optional

from album.runner import album_logging

from album.ci.utils.zenodo_api import ZenodoAPI
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import (
    force_remove,
    create_path_recursively,
    rand_folder_name,
    check_zip,
    unzip_archive,
    copy,
    copy_folder,
)
from album.core.utils.operations.url_operations import (
    is_url,
    download,
    retrieve_redirect_url,
    download_resource,
)
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.model.coordinates import Coordinates

module_logger = album_logging.get_active_logger


def clean_resolve_tmp(tmp_cache_dir) -> None:
    """Cleans the temporary directory which might have been used during resolving."""
    force_remove(tmp_cache_dir)
    create_path_recursively(tmp_cache_dir)


def get_attributes_from_string(str_input: str) -> dict:
    """Interprets a string input if in valid format and returns necessary attributes dictionary.

    Args:
        str_input:
            The string input. Supported formats:
                doi:  <doi>:<prefix>/<suffix> or <prefix>/<suffix> of a solution
                gnv: <group>:<name>:<version> of a solution
                cgnv: <catalog>:<group>:<name>:<version> of a solution
                url: any url pointing to a solution file

    Returns:
        Dictionary of either grp name version, catalog grp name version or doi

    """
    attrs_dict = get_doi_from_input(str_input)
    if not attrs_dict:
        attrs_dict = get_gnv_from_input(str_input)
        if not attrs_dict:
            attrs_dict = get_cgnv_from_input(str_input)
            if not attrs_dict:
                raise ValueError(
                    "Invalid input format: %s! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> "
                    "or <group>:<name>:<version> or <catalog>:<group>:<name>:<version> "
                    "or point to a valid file! Aborting..." % str_input
                )
    module_logger().debug("Parsed %s from the input... " % attrs_dict)
    return attrs_dict


def get_gnv_from_input(str_input: str):
    """Parses Group, Name, Version from input, separated by ":"."""
    s = re.search("^([^:]+):([^:]+):([^:]+)$", str_input)

    if s:
        return {"group": s.group(1), "name": s.group(2), "version": s.group(3)}
    return None


def get_cgnv_from_input(str_input: str):
    """Parses Catalog, Group, Name, Version from input, separated by ":"."""
    s = re.search("^([^:]+):([^:]+):([^:]+):([^:]+)$", str_input)

    if s:
        return {
            "catalog": s.group(1),
            "group": s.group(2),
            "name": s.group(3),
            "version": s.group(4),
        }
    return None


def get_doi_from_input(str_input: str):
    """Parses the DOI from string input."""
    s = re.search("^(^doi:)?([^:\/]*\/[^:\/]*)$", str_input)
    if s:
        return {"doi": s.group(2)}
    return None


def is_pathname_valid(pathname: str) -> bool:
    """Checks if a pathname is valid for the current OS

    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.
    source: https://stackoverflow.com/a/34102855
    """
    # Windows-specific error code indicating an invalid pathname.
    # Sadly, Python fails to provide the following magic number for us.
    ERROR_INVALID_NAME = 123
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = (
            os.environ.get("HOMEDRIVE", "C:")
            if sys.platform == "win32"
            else os.path.sep
        )
        assert os.path.isdir(root_dirname)  # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, "winerror"):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.


def check_doi(doi, tmp_cache_dir):
    tmp_cache_dir = Path(tmp_cache_dir).joinpath(rand_folder_name())

    link = "https://doi.org/" + doi  # e.g. 10.5281/zenodo.5571504

    url = retrieve_redirect_url(link)

    link_to_solution_zip = parse_doi_service_url(url)

    p = download_resource(link_to_solution_zip, tmp_cache_dir.joinpath("solution.zip"))

    return prepare_path(p, tmp_cache_dir)


def parse_doi_service_url(url):
    if re.search("https:\/\/[a-zA-Z.]*zenodo[.]org\/", url):
        link = _parse_zenodo_url(url)
    else:
        raise NotImplementedError("DOI service not supported!")

    return link


def _parse_zenodo_url(url):
    g = re.search("(https:\/\/[a-zA-Z.]*zenodo[.]org\/)(record)[\/]([0-9]*)$", url)

    if g:
        record_id = g.group(3)

        return retrieve_zenodo_record_download_zip(record_id)
    else:
        raise ValueError("Unknown zenodo URL format!...")


def retrieve_zenodo_record_download_zip(record_id):
    query = ZenodoAPI()

    record = query.records_get(record_id)[0]

    file_dl = None
    for file in record.files:
        if re.search(
            "[.]zip$", file.key
        ):  # there is only a single zip file in the record
            file_dl = file.get_download_link()

    if not file_dl:
        raise ValueError(
            'No valid zip file found int the zenodo record with id "%s"!' % record_id
        )

    return file_dl


def check_file_or_url(path, tmp_cache_dir):
    """Resolves a path or url. Independent of catalogs."""
    if is_url(path):
        p = download(str(path), base=tmp_cache_dir)
    elif is_pathname_valid(path) and (os.path.isfile(path) or os.path.isdir(path)):
        p = Path(path)
    else:
        return None

    return prepare_path(p, tmp_cache_dir)


def prepare_path(path, tmp_cache_dir):
    """Prepares the path to be run in album. Returning path points to the solution file.

    Args:
        path:
            The path pointing to a zip, file, or folder suited to be run in album.
        tmp_cache_dir:
            The temporary cache dir to extract/copy files to.

    Returns:
        The path pointing to the python file executable in album.

    """
    p = Path(path)
    if p.exists():
        # copying to tmp-dir necessary for cloning
        target_folder = tmp_cache_dir.joinpath(rand_folder_name())
        if p.is_file():  # zip or file
            if check_zip(p):  # zip file
                p = unzip_archive(p, target_folder)
                p = p.joinpath(DefaultValues.solution_default_name.value)
            else:  # python file
                p = copy(
                    p, target_folder.joinpath(DefaultValues.solution_default_name.value)
                )
        elif p.is_dir():  # unzipped zip
            p = copy_folder(p, target_folder, copy_root_folder=False)
            p = p.joinpath(DefaultValues.solution_default_name.value)

        return p


def dict_to_coordinates(solution_attr) -> ICoordinates:
    if not all([k in solution_attr.keys() for k in ["name", "version", "group"]]):
        raise ValueError(
            "Cannot resolve solution! Group, name and version must be specified!"
        )
    return Coordinates(
        group=solution_attr["group"],
        name=solution_attr["name"],
        version=solution_attr["version"],
    )


def get_zip_name(coordinates: ICoordinates):
    return get_zip_name_prefix(coordinates) + ".zip"


def get_zip_name_prefix(coordinates: ICoordinates):
    return "_".join([coordinates.group(), coordinates.name(), coordinates.version()])


def build_resolve_string(
    resolve_solution_dict: dict, catalog: Optional[ICatalog] = None
):
    if "doi" in resolve_solution_dict.keys():
        resolve_solution = resolve_solution_dict["doi"]
    elif all([x in resolve_solution_dict.keys() for x in ["group", "name", "version"]]):
        resolve_solution = ":".join(
            [
                resolve_solution_dict["group"],
                resolve_solution_dict["name"],
                resolve_solution_dict["version"],
            ]
        )

        if catalog:
            resolve_solution = ":".join([catalog.name(), resolve_solution])

    elif "resolve_solution" in resolve_solution_dict.keys():
        resolve_solution = resolve_solution_dict["resolve_solution"]
    else:
        raise ValueError("Invalid declaration of parent or step!")

    return resolve_solution


def get_parent(
    parent_collection_entry: ICollectionIndex.ICollectionSolution,
) -> ICollectionIndex.ICollectionSolution:
    """Given an collection entry (aka row of the collection table) this method returns the corresponding parent"""
    if parent_collection_entry.internal()["parent"]:
        parent = parent_collection_entry.internal()["parent"]
        while parent.internal()["parent"]:
            parent = parent["parent"]

        return parent
    return parent_collection_entry


def as_tag(coordinates: ICoordinates) -> str:
    return "-".join([coordinates.group(), coordinates.name(), coordinates.version()])


def as_tag_unversioned(coordinates: ICoordinates) -> str:
    return "-".join([coordinates.group(), coordinates.name()])
