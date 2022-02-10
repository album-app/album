import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple, List, Generator

import validators
from git import Repo, GitCommandError

from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_index import ICatalogIndex
from album.core.model.catalog_index import CatalogIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy, copy_folder, write_dict_to_json, force_remove
from album.core.utils.operations.git_operations import download_repository, init_repository, clone_repository, \
    checkout_files
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution

module_logger = album_logging.get_active_logger


def download_index_files(src, tmp_dir: Path, branch_name="main") -> Tuple[Path, Path]:
    tmp_dir = Path(tmp_dir)
    with clone_repository(src, branch_name, tmp_dir) as repo:
        checkout_files(repo, [DefaultValues.catalog_index_metafile_json.value])
        try:
            checkout_files(repo, [DefaultValues.catalog_index_file_name.value])
        except GitCommandError as e:
            # catalog index file does not have to be present for empty catalogs
            if 'did not match any file' not in str(e):
                raise e
    index_src = tmp_dir.joinpath(DefaultValues.catalog_index_file_name.value)
    index_meta_src = tmp_dir.joinpath(DefaultValues.catalog_index_metafile_json.value)
    return index_src, index_meta_src


def get_index_dir(src) -> Tuple[Path, Path]:
    index_src = Path(src).joinpath(DefaultValues.catalog_index_file_name.value)
    index_meta_src = Path(src).joinpath(DefaultValues.catalog_index_metafile_json.value)
    return index_src, index_meta_src


class Catalog(ICatalog):

    def __init__(self, catalog_id, name, path, src=None, deletable=True, branch_name="main", catalog_type="direct"):
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
            catalog_type:
                The type of the catalog. Either "direct" or "request". Important during deployment.

        """
        self._catalog_id = catalog_id
        self._name = name
        self._src = src
        self._version = None  # is set automatically with the index
        self._catalog_index: Optional[ICatalogIndex] = None
        self._path = Path(path)
        self._branch_name = branch_name

        self._is_deletable = deletable

        self._solution_list_path = self._path.joinpath(DefaultValues.catalog_solution_list_file_name.value)
        self._meta_path = self._path.joinpath(DefaultValues.catalog_index_metafile_json.value)
        self._index_path = self._path.joinpath(DefaultValues.catalog_index_file_name.value)
        self._type = catalog_type

        if self.is_local() and self._src:
            self._src = Path(self._src).absolute()

    def __eq__(self, other):
        return isinstance(other, ICatalog) and \
               other.catalog_id() == self._catalog_id

    def __del__(self):
        self.dispose()

    def dispose(self):
        if self._catalog_index is not None:
            self._catalog_index.close()

    def is_cache(self):
        """Returns Boolean indicating whether the catalog is used for caching only."""
        return self._src is None or self.is_local() and self._path.exists() and os.path.samefile(
            str(self._src), self._path
        )

    def is_local(self):
        """Returns Boolean indicating whether the catalog is remote or local."""
        return not validators.url(str(self._src))

    def update_index_cache_if_possible(self, tmp_dir):
        try:
            self.update_index_cache(tmp_dir)
        except AssertionError:
            module_logger().warning("Could not refresh index. Source invalid!")
            return False
        except ConnectionError:
            module_logger().warning("Could not refresh index. Connection error!")
            return False
        except FileNotFoundError:
            module_logger().warning("Could not refresh index. Source not found!")
            return False
        except GitCommandError as e:
            module_logger().warning("Could not refresh index. Git command failed:")
            module_logger().warning(e)
            return False
        except Exception as e:
            module_logger().warning("Could not refresh index. Unknown reason!")
            module_logger().warning(e)
            return False

        return True

    def update_index_cache(self, tmp_dir):
        if self.is_cache():
            return False

        if self.is_local():
            index_available = self._copy_index_from_src_to_cache()
        else:
            index_available = self._update_remote_index(tmp_dir)

        if not index_available:
            self.dispose()
        return True

    def add(self, active_solution: ISolution, force_overwrite=False):
        solution_attrs = get_deploy_dict(active_solution)

        if active_solution.setup().doi:
            solution_attrs["doi"] = active_solution.setup().doi
            if self._catalog_index.get_solution_by_doi(solution_attrs["doi"]) is not None:
                if force_overwrite:
                    module_logger().warning("Solution already exists! Overwriting...")
                else:
                    raise RuntimeError("DOI already exists in catalog! Aborting...")

        if active_solution.setup().deposit_id:
            solution_attrs["deposit_id"] = active_solution.setup().deposit_id

        lookup_solution = self._catalog_index.get_solution_by_coordinates(active_solution.coordinates())
        if lookup_solution:
            if force_overwrite:
                module_logger().warning("Solution already exists! Overwriting...")
            else:
                raise RuntimeError("Solution already exists in catalog! Aborting...")

        self._catalog_index.update(active_solution.coordinates(), solution_attrs)
        self._catalog_index.save()
        self._catalog_index.export(self._solution_list_path)

    def remove(self, active_solution: ISolution):
        if self.is_local():
            solution_attrs = get_deploy_dict(active_solution)
            solution_entry = self._catalog_index.remove_solution_by_group_name_version(
                dict_to_coordinates(solution_attrs)
            )
            if solution_entry:
                self._catalog_index.export(self._solution_list_path)
            else:
                module_logger().warning("Solution not installed! Doing nothing...")
        else:
            module_logger().warning("Cannot remove entries from a remote catalog! Doing nothing...")

    def _update_remote_index(self, tmp_dir):
        repo_dir = Path(tmp_dir).joinpath('repo')
        try:
            src, meta_src = download_index_files(self.src(), repo_dir, branch_name=self.branch_name())
            self._copy_index_to_cache(src, meta_src)
            index_available = src.exists()
            return index_available
        finally:
            force_remove(repo_dir)

    def _copy_index_from_src_to_cache(self) -> bool:
        src_path_index = Path(self._src).joinpath(DefaultValues.catalog_index_file_name.value)
        src_path_meta = Path(self._src).joinpath(DefaultValues.catalog_index_metafile_json.value)
        return self._copy_index_to_cache(src_path_index, src_path_meta)

    def _copy_index_to_cache(self, db_file, meta_file):
        # check if meta information valid, only then continue
        if not meta_file.exists():
            raise FileNotFoundError("Could not find file %s..." % meta_file)

        module_logger().debug("Copying meta information from %s to %s..." % (meta_file, self._meta_path))
        copy(meta_file, self._meta_path)

        if db_file.exists():
            module_logger().debug("Copying index from %s to %s..." % (db_file, self._index_path))
            copy(db_file, self._index_path)
        else:
            if self._index_path.exists():
                force_remove(self._index_path)
                return False
            else:
                module_logger().debug("Index file of the catalog does not exist yet...")
        return True

    def copy_index_from_cache_to_src(self):
        src_path_index = Path(self._src).joinpath(DefaultValues.catalog_index_file_name.value)

        if not src_path_index.exists():
            if not self._index_path.parent.exists():
                self._index_path.parent.mkdir(parents=True)

        module_logger().debug("Copying index from %s to %s..." % (self._index_path, src_path_index))
        copy(self._index_path, src_path_index)
        src_path_solution_list = Path(self._src).joinpath(DefaultValues.catalog_solution_list_file_name.value)

        module_logger().debug(
            "Copying exported index from %s to %s..." % (self._solution_list_path, src_path_solution_list)
        )
        copy(self._solution_list_path, src_path_solution_list)

    @contextmanager
    def retrieve_catalog(self, path=None, force_retrieve=False, update=True) -> Generator[Repo, None, None]:
        if self.is_cache():
            raise RuntimeError("Cannot retrieve a cache catalog as no source exists!")

        path = Path(path) if path else self._path

        if self.is_local():  # case src is not downloadable
            copy_folder(self._src, path, copy_root_folder=False, force_copy=True)
            repo = init_repository(path)
        else:  # case src is downloadable
            module_logger().debug("Trying to retrieve catalog %s to the path %s..." % (self._name, str(path)))
            repo = download_repository(self._src, str(path), force_download=force_retrieve, update=update)

        yield repo
        repo.close()

    def write_catalog_meta_information(self):
        d = self.get_meta_information()
        write_dict_to_json(self._meta_path, d)

    def get_meta_information(self):
        return {
            "name": self._name,
            "version": self._version,
            "type": self._type
        }

    def get_all_solution_versions(self, group: str, name: str) -> List[Solution]:
        versions = self._catalog_index.get_all_solution_versions(group, name)
        res = []
        for version in versions:
            res.append(Solution(attrs=version))
        return res

    def load_index(self):
        self._catalog_index = CatalogIndex(self._name, self._index_path)

    def catalog_id(self) -> int:
        return self._catalog_id

    def name(self) -> str:
        return self._name

    def src(self) -> Path:
        return self._src

    def version(self) -> str:
        return self._version

    def index(self) -> ICatalogIndex:
        return self._catalog_index

    def path(self) -> Path:
        return self._path

    def branch_name(self) -> str:
        return self._branch_name

    def is_deletable(self) -> bool:
        return self._is_deletable

    def solution_list_path(self) -> Path:
        return self._solution_list_path

    def index_path(self) -> Path:
        return self._index_path

    def type(self) -> str:
        return self._type

    def set_catalog_id(self, catalog_id):
        self._catalog_id = catalog_id

    def set_version(self, version):
        self._version = version
