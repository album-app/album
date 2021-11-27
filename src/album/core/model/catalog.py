import os
import re
from pathlib import Path
from typing import Optional

import validators
from git import Repo

from album.core.model.catalog_index import CatalogIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy, copy_folder, write_dict_to_json, force_remove
from album.core.utils.operations.git_operations import download_repository, init_repository
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.core.utils.operations.url_operations import download_resource
from album.runner import album_logging, Solution
from album.runner.model.coordinates import Coordinates

module_logger = album_logging.get_active_logger


def get_index_url(src, branch_name="main"):
    """Gets the download link for an index."""
    index_src = re.sub(r"\.git$", "", src) + "/-/raw/%s/%s" % (branch_name, DefaultValues.catalog_index_file_name.value)
    index_meta_src = re.sub(r"\.git$", "", src) + "/-/raw/%s/%s" % (
        branch_name, DefaultValues.catalog_index_metafile_json.value
    )
    return index_src, index_meta_src


def get_index_dir(src):
    """Gets the download directory for an index."""
    index_src = Path(src).joinpath(DefaultValues.catalog_index_file_name.value)
    index_meta_src = Path(src).joinpath(DefaultValues.catalog_index_metafile_json.value)
    return index_src, index_meta_src


def get_solution_src(src, coordinates: Coordinates, branch_name="main"):
    """Gets the download link for a solution."""
    return re.sub(r"\.git$", "", src) + "/-/raw/%s/solutions/%s/%s/%s/%s" % (
        branch_name, coordinates.group, coordinates.name, coordinates.version,
        "%s_%s_%s%s" % (coordinates.group, coordinates.name, coordinates.version, ".zip")
    )


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

    def __init__(self, catalog_id, name, path, src=None, deletable=True, branch_name="main"):
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
            branch_name:
                When a git based catalog this attribute can be set to use other branches than the main branch (default)
        """
        self.catalog_id = catalog_id
        self.name = name
        self.src = src
        self.version = None  # is set automatically with the index
        self.catalog_index: Optional[CatalogIndex] = None
        self.path = Path(path)
        self.branch_name = branch_name

        self.is_deletable = deletable

        self.solution_list_path = self.path.joinpath(DefaultValues.catalog_solution_list_file_name.value)
        self._meta_path = self.path.joinpath(DefaultValues.catalog_index_metafile_json.value)
        self.index_path = self.path.joinpath(DefaultValues.catalog_index_file_name.value)

    def __eq__(self, other):
        return isinstance(other, Catalog) and \
               other.catalog_id == self.catalog_id

    def __del__(self):
        self.dispose()

    def dispose(self):
        if self.catalog_index is not None:
            self.catalog_index.close()

    def is_cache(self):
        """Returns Boolean indicating whether the catalog is used for caching only."""
        return self.src is None or self.is_local() and self.path.exists() and os.path.samefile(self.src, self.path)

    def is_local(self):
        """Returns Boolean indicating whether the catalog is remote or local."""
        return not validators.url(str(self.src))

    def update_index_cache_if_possible(self):
        try:
            self.update_index_cache()
        except AssertionError:
            module_logger().warning("Could not refresh index. Source invalid!")
            return False
        except ConnectionError:
            module_logger().warning("Could not refresh index. Connection error!")
            return False
        except FileNotFoundError:
            module_logger().warning("Could not refresh index. Source not found!")
            return False
        except Exception as e:
            module_logger().warning("Could not refresh index. Unknown reason!")
            module_logger().warning(e)
            return False

        return True

    def update_index_cache(self):
        """Updates the cache index file and metadata of a catalog.

        Returns
            True when updated successfully, else False.

        """
        if self.is_cache():
            return False

        if self.is_local():
            index_available = self.copy_index_from_src_to_cache()
        else:
            index_available = self.download_index()

        if not index_available:
            self.dispose()
            # index got deleted in src so we do the same locally
            force_remove(self.index_path)
        return True

    def add(self, active_solution: Solution, force_overwrite=False):
        """Adds an active solution_object to the index. Does not copy anything from A to B.
        Expects the local catalog index to be loaded.

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
        solution_attrs = get_deploy_dict(active_solution)

        if active_solution.setup.doi:
            solution_attrs["doi"] = active_solution.setup.doi
            if self.catalog_index.get_solution_by_doi(solution_attrs["doi"]) is not None:
                if force_overwrite:
                    module_logger().warning("Solution already exists! Overwriting...")
                else:
                    raise RuntimeError("DOI already exists in catalog! Aborting...")

        if active_solution.setup.deposit_id:
            solution_attrs["deposit_id"] = active_solution.setup.deposit_id

        lookup_solution = self.catalog_index.get_solution_by_coordinates(active_solution.coordinates)
        if lookup_solution:
            if force_overwrite:
                module_logger().warning("Solution already exists! Overwriting...")
            else:
                raise RuntimeError("Solution already exists in catalog! Aborting...")

        self.catalog_index.update(active_solution.coordinates, solution_attrs)
        self.catalog_index.save()
        self.catalog_index.export(self.solution_list_path)

    def remove(self, active_solution: Solution):
        """Removes a solution from a catalog. Only for local catalogs. Expects the local catalog index to be loaded.

        Args:
            active_solution:
                The active solution object to remove from the catalog.

        """
        if self.is_local():
            solution_attrs = get_deploy_dict(active_solution)
            solution_entry = self.catalog_index.remove_solution_by_group_name_version(
                dict_to_coordinates(solution_attrs)
            )
            if solution_entry:
                self.catalog_index.export(self.solution_list_path)
            else:
                module_logger().warning("Solution not installed! Doing nothing...")
        else:
            module_logger().warning("Cannot remove entries from a remote catalog! Doing nothing...")

    def copy_index_from_src_to_cache(self) -> bool:
        """Copy the index file of a catalog and its metadata to the catalog cache folder.

        Returns:
            Index availability: True when the index was available, false when the catalog has no index file in the src.
        """
        src_path_index = Path(self.src).joinpath(DefaultValues.catalog_index_file_name.value)
        src_path_meta = Path(self.src).joinpath(DefaultValues.catalog_index_metafile_json.value)

        # check if meta information valid, only then continue
        if not src_path_meta.exists():
            raise FileNotFoundError("Could not find file %s..." % src_path_meta)

        module_logger().debug("Copying meta information from %s to %s..." % (src_path_meta, self._meta_path))
        copy(src_path_meta, self._meta_path)

        if src_path_index.exists():
            module_logger().debug("Copying index from %s to %s..." % (src_path_index, self.index_path))
            copy(src_path_index, self.index_path)
        else:
            if self.index_path.exists():
                # case index was deleted in the src
                return False
            else:
                module_logger().debug("Index file of the catalog does not exist yet...")
        return True

    def copy_index_from_cache_to_src(self):
        """Copy the index file of a catalog and its metadata from the catalog cache folder into the source folder."""
        src_path_index = Path(self.src).joinpath(DefaultValues.catalog_index_file_name.value)

        if not src_path_index.exists():
            if not self.index_path.parent.exists():
                self.index_path.parent.mkdir(parents=True)

        module_logger().debug("Copying index from %s to %s..." % (self.index_path, src_path_index))
        copy(self.index_path, src_path_index)
        src_path_solution_list = Path(self.src).joinpath(DefaultValues.catalog_solution_list_file_name.value)

        module_logger().debug(
            "Copying exported index from %s to %s..." % (self.solution_list_path, src_path_solution_list)
        )
        copy(self.solution_list_path, src_path_solution_list)

    def download_index(self) -> bool:
        """Downloads the index file of the catalog and its metadata.

        Returns
            Index availability: True when the index was available, false when the catalog has no index file in the src.
        """
        src, meta_src = get_index_url(self.src, self.branch_name)

        # check metadata first before moving on
        download_resource(meta_src, self._meta_path)

        try:
            download_resource(src, self.index_path)
        except AssertionError:
            # catalogs don't necessary have an index file. There simply might not be one yet or it got deleted.
            return False

        return True

    def retrieve_catalog(self, path=None, force_retrieve=False, update=True) -> Optional[Repo]:
        """Downloads or copies the whole catalog from its source. Used for deployment.

        Args:
            force_retrieve:
                Boolean, indicates whether to force delete content of path or not
            path:
                The path to download to (optional). Catalog path is taken if no path specified.
            update:
                If catalog already exists - flag to indicate a hard reset to the repository.

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
            module_logger().debug("Trying to retrieve catalog %s to the path %s..." % (self.name, str(path)))
            repo = download_repository(self.src, str(path), force_download=force_retrieve, update=update)

            return repo

    def write_catalog_meta_information(self):
        d = self.get_meta_information()
        write_dict_to_json(self._meta_path, d)

    def get_meta_information(self):
        return {
            "name": self.name,
            "version": self.version
        }

    def get_all_solution_versions(self, group: str, name: str):
        versions = self.catalog_index.get_all_solution_versions(group, name)
        res = []
        for version in versions:
            res.append(Solution(attrs=version))
        return res

    def load_index(self):
        self.catalog_index = CatalogIndex(self.name, self.index_path)

