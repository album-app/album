import os
import re
from pathlib import Path
from typing import Optional

import validators

from album.ci.utils.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog_index import CatalogIndex
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.group_name_version import GroupNameVersion
from album.core.utils.operations.file_operations import unzip_archive, copy, copy_folder, get_dict_from_json, \
    write_dict_to_json
from album.core.utils.operations.git_operations import download_repository, init_repository
from album.core.utils.operations.resolve_operations import get_zip_name, dict_to_group_name_version
from album.core.utils.operations.url_operations import download_resource
from album_runner import logging

module_logger = logging.get_active_logger


# todo: how to do that efficiently? Download the whole catalog? Or only the index and then the corresp.
#  solutions whenever they are used?
def get_index_url(src):
    """Gets the download link for an index."""
    # todo: "main" is still hardcoded! :(
    index_src = re.sub(r"\.git$", "", src) + "/-/raw/main/%s" % DefaultValues.catalog_index_file_name.value
    index_meta_src = re.sub(r"\.git$", "", src) + "/-/raw/main/%s" % DefaultValues.catalog_index_file_json.value
    return index_src, index_meta_src


def get_index_dir(src):
    """Gets the download link for an index."""
    # todo: "main" is still hardcoded! :(
    index_src = Path(src).joinpath(DefaultValues.catalog_index_file_name.value)
    index_meta_src = Path(src).joinpath(DefaultValues.catalog_index_file_json.value)
    return index_src, index_meta_src


# todo: this is not good! Think of smth. clever here
def get_solution_src(src, group_name_version: GroupNameVersion):
    """Gets the download link for a solution in an index."""
    # todo: "main" is still hardcoded! :(
    return re.sub(r"\.git$", "", src) + "/-/raw/main/solutions/%s/%s/%s/%s" \
           % (group_name_version.group, group_name_version.name, group_name_version.version, 
              "%s_%s_%s%s" % (group_name_version.group, group_name_version.name, group_name_version.version, ".zip"))


class Catalog:
    """Class handling a Catalog.

    An album catalog contains solution files. These files are python scripts which can be interpreted by the album
    framework and implement a routine for solving a problem of any kind. The Catalog has an index where the solution
    files and its metadata are stored in a hierarchical way. This class brings all the functionality to resolve, add,
    remove solutions from a Catalog, whereas resolving refers to the act of looking up, if a solution exists in the
    catalog. A catalog can be local or remote. If the catalog is remote, solutions cannot be
    added or removed to/from it. (see deploy for context)

    Attributes:
        name:
            The ID of the catalog. Usually a string. Can be compared to a name.
        src:
            The source of the catalog. Gitlab/github link or path.
        catalog_index:
            The Index object of the catalog. A tree like structure.
        path:
            The path to the catalog cache.
        _meta_path:
            The path to the catalog meta cache. Relative to the path attribute.
        index_path:
            The path to the catalog index cache. Relative to the path attribute.
        solution_list_path:
            The path to the catalog solution list cache. Relative to the path attribute.

    """
    # default prefix how to organize solutions. gnv = Group Name Version folder structure.
    gnv_solution_prefix = DefaultValues.cache_path_solution_prefix.value

    def __init__(self, catalog_id, name, path, src=None, deletable=True):
        """Init routine.

        Args:
            catalog_id:
                The id of the catalog in the collection.
            name:
                The name of the catalog.
            path:
                The absolute path to the catalog.
            src:
                The source of the catalog (Default: None)
                Can be a URL, a git-link, a path to a network-device or a path to any other storage system.
            deletable:
                Boolean to indicate whether the catalog is deletable or not. Relevant for a collection of catalogs.
        """
        self.catalog_id = catalog_id
        self.name = name
        self.src = src
        self.version = None  # is set automatically with the index
        self.catalog_index: Optional[CatalogIndex] = None
        self.path = Path(path)

        self.is_deletable = deletable

        self.solution_list_path = self.path.joinpath(DefaultValues.catalog_solution_list_file_name.value)
        self._meta_path = self.path.joinpath(DefaultValues.catalog_index_file_json.value)

        # initialize the index
        self.index_path = self.path.joinpath(DefaultValues.catalog_index_file_name.value)

    def is_cache(self):
        """Returns Boolean indicating whether the catalog is used for caching only."""
        return self.is_local() and self.path.exists() and os.path.samefile(self.src, self.path)

    def is_local(self):
        """Returns Boolean indicating whether the catalog is remote or local."""
        return not validators.url(str(self.src))

    def resolve(self, group_name_version: GroupNameVersion):
        """Resolves (also: finds, looks up) a solution in the catalog, returning the absolute path to the solution file.

        Args:
            group_name_version:
                The group affiliation, name, and version of the solution.

        Returns: the path to the solution file.

        """
        solution_entry = self.catalog_index.get_solution_by_group_name_version(group_name_version)

        if solution_entry:
            path_to_solution = self.get_solution_file(group_name_version)

            return path_to_solution

        return None  # could not resolve

    def resolve_doi(self, doi):
        """Resolves an album via doi. Returns the absolute path to the solution.

        Args:
            doi:
                The doi of the solution

        Returns:
            Absolute path to the solution file.

        """
        solution_entry = self.catalog_index.get_solution_by_doi(doi)

        if solution_entry:
            path_to_solution = self.get_solution_file(
                dict_to_group_name_version(solution_entry)
            )

            return path_to_solution

        return None  # could not resolve

    def get_solution_path(self, group_name_version: GroupNameVersion):
        """Gets the cache path of a solution given its group, name and version.

        Args:
            group_name_version:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return self.path.joinpath(Configuration.get_solution_path_suffix(group_name_version))

    def get_solution_file(self, group_name_version: GroupNameVersion):
        """Gets the file to the solution.py file of the extracted solution.zip living inside the catalog.

        Args:
            group_name_version:
                The group affiliation, name, and version of the solution.

        Returns:
            The path where the file is supposed to be once the zip is extracted during installation.

        """
        p = self.get_solution_path(group_name_version).joinpath(DefaultValues.solution_default_name.value)

        return p

    def get_solution_zip(self, group_name_version: GroupNameVersion):
        """Gets the cache zip of a solution given its group, name and version living inside the catalog.

        Args:
            group_name_version:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the solution.py cache file.

        """
        return self.get_solution_path(group_name_version).joinpath(get_zip_name(group_name_version))

    @staticmethod
    def get_solution_zip_suffix(group_name_version: GroupNameVersion):
        """Gets the cache zip suffix of a solution given its group, name and version living inside the catalog.

        Args:
            group_name_version:
                The group affiliation, name, and version of the solution.

        Returns:
            The absolute path to the cache folder of the solution.

        """
        return Path("").joinpath(Configuration.get_solution_path_suffix(group_name_version), get_zip_name(group_name_version))

    # todo: write tests
    def download_solution_via_doi(self, doi, solution_name):
        """Downloads the solution via its doi.

        Args:
            doi:
                The DOI of the solution.
            solution_name:
                The name of the solution

        Returns:
            The absolute path of the downloaded solution.

        Raises:
            RuntimeError if the solution cannot be found in the online resource
                         if the DOI is not unique.

        """
        raise NotImplementedError
        # Todo: replace with non-sandbox version
        zenodo_api = ZenodoAPI(ZenodoDefaultUrl.sandbox_url.value, None)

        # todo: maybe there is a nicer way than parsing stuff from the DOI?
        record_id = doi.split(".")[-1]
        record_list = zenodo_api.records_get(record_id)

        if not record_list:
            raise RuntimeError("Could not receive solution from doi %s. Aborting..." % doi)

        if len(record_list) > 1:
            raise RuntimeError("Doi %s is not unique. Aborting..." % doi)

        record = record_list[0]

        url = record.files[solution_name].get_download_link()

        download_resource(url, self.get_doi_cache_file(doi))

        return self.path.joinpath(self.doi_solution_prefix, doi)

    def retrieve_solution(self, group_name_version: GroupNameVersion):
        """Downloads or copies a solution from the catalog to the local resource (cache path of the catalog).

        Args:
            group_name_version:
                The group affiliation, name, and version of the solution.
        Returns:
            The absolute path of the downloaded solution.

        """
        if self.is_cache():  # no src to download form or src to copy from
            raise RuntimeError("Cannot download from a cache catalog!")

        elif self.is_local():  # src to copy from
            src_path = Path(self.src).joinpath(self.get_solution_zip_suffix(group_name_version))
            solution_zip_file = self.get_solution_zip(group_name_version)
            copy(src_path, solution_zip_file)

        else:  # src to download from
            url = get_solution_src(self.src, group_name_version)
            solution_zip_file = self.get_solution_zip(group_name_version)
            download_resource(url, solution_zip_file)

        solution_zip_path = unzip_archive(solution_zip_file)
        solution_path = solution_zip_path.joinpath(DefaultValues.solution_default_name.value)

        return solution_path

    def load_index(self):
        """Loads the index from file or src. If a file and src exists routine tries to update the index."""
        if self.is_cache():
            raise RuntimeError("Cache catalog does not have it's own index - all solutions are indexed in the collection index.")
        if not self.index_path.is_file():  # only download/copy from src if index does not exist yet
            if self.is_local():  # case where src is not downloadable
                # copy catalog from local resource to cache location
                self.copy_index_from_src_to_cache()
            else:
                # load catalog from remote src
                self.download_index()

        self.catalog_index = MigrationManager().create_catalog_index(self.index_path, self.name, CatalogIndex.version)
        self.version = self.get_version()

    def get_version(self):
        database_version = self.catalog_index.get_version()
        meta_dict = self.retrieve_catalog_meta_information(self.path)
        if meta_dict:
            meta_version = meta_dict['version']
        else:
            # no meta file found / dict is empty, just use default version
            meta_version = CatalogIndex.version
            module_logger().warning(f"No meta information for catalog {self.name} found, assuming database version {meta_version}")

        if database_version != meta_version:
            raise ValueError(f"Catalog meta information (version {meta_version}) unequal to actual version {database_version}!")

        return database_version

    def refresh_index(self) -> bool:
        """Routine to refresh the catalog index. Downloads or copies the index_file."""
        if self.is_cache():
            return False

        if self.is_local():  # case src not downloadable
            self.copy_index_from_src_to_cache()
        else:
            try:
                self.download_index()
            except AssertionError:
                module_logger().warning("Could not refresh index. Source invalid!")
                return False
            except ConnectionError:
                module_logger().warning("Could not refresh index. Connection error!")
                return False
            except Exception as e:
                module_logger().warning("Could not refresh index. Unknown reason!")
                module_logger().warning(e)
                return False

        self.catalog_index = MigrationManager().create_catalog_index(self.index_path, self.name, CatalogIndex.version)
        return True

    def add(self, active_solution, force_overwrite=False):
        """Adds an active solution_object to the index. Does not copy anything from A to B.

        Args:
            active_solution:
                The active album object (also: solution object, see AlbumClass) to add to the catalog.
            force_overwrite:
                When True forces adding a solution which already exists in the catalog. Only valid for solutions without
                DOI. (Default: False)

        Raises:
            RuntimeError when the DOI metadata information of a album object already exists in the catalog.
                         when the solution already exists and force_overwrite is False.

        """
        solution_attrs = active_solution.get_deploy_dict()

        if hasattr(active_solution, "doi"):
            solution_attrs["doi"] = getattr(active_solution, "doi")
            if self.catalog_index.get_solution_by_doi(solution_attrs["doi"]) is not None:
                if force_overwrite:
                    module_logger().warning("Solution already exists! Overwriting...")
                else:
                    raise RuntimeError("DOI already exists in catalog! Aborting...")

        if hasattr(active_solution, "deposit_id"):
            solution_attrs["deposit_id"] = getattr(active_solution, "deposit_id")

        if not self.catalog_index:
            self.load_index()
        if self.catalog_index.get_solution_by_group_name_version(
                dict_to_group_name_version(solution_attrs)
        ) is not None:
            if force_overwrite:
                module_logger().warning("Solution already exists! Overwriting...")
            else:
                raise RuntimeError("Solution already exists in catalog! Aborting...")

        self.catalog_index.update(solution_attrs)
        self.catalog_index.save()
        self.catalog_index.export(self.solution_list_path)

    def remove(self, active_solution):
        """Removes a solution from a catalog. Only for local catalogs.

        Args:
            active_solution:
                The active album object (also: solution object, see AlbumClass) to remove from the catalog.

        """
        if self.is_local():
            solution_attrs = active_solution.get_deploy_dict()

            if not self.catalog_index:
                self.load_index()
            solution_entry = self.catalog_index.remove_solution_by_group_name_version(
                dict_to_group_name_version(solution_attrs)
            )
            if solution_entry:
                self.catalog_index.export(self.solution_list_path)
            else:
                module_logger().warning("Solution not installed! Doing nothing...")
        else:
            module_logger().warning("Cannot remove entries from a remote catalog! Doing nothing...")

    def copy_index_from_src_to_cache(self):
        """Copy the index file of a catalog and its metadata to the catalog cache folder."""
        src_path_index = Path(self.src).joinpath(DefaultValues.catalog_index_file_name.value)
        src_path_meta = Path(self.src).joinpath(DefaultValues.catalog_index_file_json.value)

        if not src_path_index.exists():
            if not self.index_path.parent.exists():
                self.index_path.parent.mkdir(parents=True)
        else:
            copy(src_path_index, self.index_path)

        if not src_path_meta.exists():
            return FileNotFoundError("Could not find file %s..." % src_path_meta)

        copy(src_path_meta, self._meta_path)

    def copy_index_from_cache_to_src(self):
        """Copy the index file if a catalog and its metadata from the catalog cache folder into the source folder."""
        src_path_index = Path(self.src).joinpath(DefaultValues.catalog_index_file_name.value)
        if not src_path_index.exists():
            if not self.index_path.parent.exists():
                self.index_path.parent.mkdir(parents=True)
        copy(self.index_path, src_path_index)
        src_path_solution_list = Path(self.src).joinpath(DefaultValues.catalog_solution_list_file_name.value)
        copy(self.solution_list_path, src_path_solution_list)

    def download_index(self):
        """Downloads the index file of the catalog and its metadata."""
        src, meta_src = get_index_url(self.src)

        try:
            download_resource(src, self.index_path)
        except AssertionError:
            # TODO ignore that catalogs might not have a database index for now
            pass
        download_resource(meta_src, self._meta_path)

    def retrieve_catalog(self, path=None, force_retrieve=False):
        """Downloads or copies the whole catalog from its source. Used for deployment.

        Args:
            force_retrieve:
                Boolean, indicates whether to force delete content of path or not
            path:
                The path to download to (optional). Catalog path is taken if no path specified.

        Returns:
            The repository object of the catalog

        """
        if self.is_cache():
            module_logger().warning("Cannot retrieve a cache catalog as no source exists!")
            return None

        path = Path(path) if path else self.path

        if self.is_local():  # case src is not downloadable
            copy_folder(self.src, path, copy_root_folder=False, force_copy=True)
            repo = init_repository(path)

            return repo
        else:  # case src is downloadable
            module_logger().debug("Download catalog %s to the path %s..." % (self.name, str(path)))
            repo = download_repository(self.src, str(path), force_download=force_retrieve)

            return repo

    @staticmethod
    def retrieve_catalog_meta_information(identifier):
        if validators.url(str(identifier)):
            _, meta_src = get_index_url(identifier)
            meta_file = download_resource(
                meta_src, Configuration().cache_path_download.joinpath(DefaultValues.catalog_index_file_json.value)
            )
        elif Path(identifier).exists():
            _, meta_src = get_index_dir(identifier)
            if meta_src.exists():
                meta_file = copy(
                    meta_src, Configuration().cache_path_download.joinpath(DefaultValues.catalog_index_file_json.value)
                )
            else:
                raise RuntimeError("Cannot retrieve meta information for the catalog!")
        else:
            raise RuntimeError("Cannot retrieve meta information for the catalog!")

        meta_dict = get_dict_from_json(meta_file)

        return meta_dict

    def write_catalog_meta_information(self):
        d = self.get_meta_information()
        write_dict_to_json(self._meta_path, d)

    def get_meta_information(self):
        return {
            "name": self.name,
            "version": self.version
        }
