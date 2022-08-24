from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, List, Generator

from git import Repo

from album.core.api.model.catalog_index import ICatalogIndex
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution


class ICatalog:
    """Interface representing a Catalog.

    An album catalog contains solution files. These files are python scripts which can be interpreted by the album
    framework and implement a routine for solving a problem of any kind. The Catalog has an index where the solution
    files and its metadata are stored in a hierarchical way. This class brings all the functionality to resolve, add,
    remove solutions from a Catalog, whereas resolving refers to the act of looking up, if a solution exists in the
    catalog. A catalog can be local or remote. If the catalog is remote, solutions cannot be
    added or removed to/from it. (see deploy for context)

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def catalog_id(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def src(self) -> str:
        """The source of the catalog. Gitlab/github link or path."""
        raise NotImplementedError

    @abstractmethod
    def version(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def index(self) -> Optional[ICatalogIndex]:
        raise NotImplementedError

    @abstractmethod
    def path(self) -> Path:
        """The path to the catalog cache."""
        raise NotImplementedError

    @abstractmethod
    def branch_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_deletable(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_cache(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_local(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def load_index(self):
        raise NotImplementedError

    @abstractmethod
    def solution_list_path(self) -> Path:
        """The path to the catalog solution list cache."""
        raise NotImplementedError

    @abstractmethod
    def index_file_path(self) -> Path:
        """The path to the catalog index cache."""
        raise NotImplementedError

    @abstractmethod
    def set_index_path(self, path) -> Path:
        """The path to the catalog index cache."""
        raise NotImplementedError

    @abstractmethod
    def type(self) -> str:
        """The type of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def dispose(self):
        raise NotImplementedError

    @abstractmethod
    def update_index_cache_if_possible(self, tmp_dir):
        raise NotImplementedError

    @abstractmethod
    def update_index_cache(self, tmp_dir):
        raise NotImplementedError

    @abstractmethod
    def add(self, active_solution: ISolution, force_overwrite=False):
        raise NotImplementedError

    @abstractmethod
    def remove(self, coordinates: ICoordinates):
        raise NotImplementedError

    @contextmanager
    def retrieve_catalog(
        self, path=None, force_retrieve=False, update=True
    ) -> Generator[Repo, None, None]:
        yield
        raise NotImplementedError

    @abstractmethod
    def get_meta_information(self):
        raise NotImplementedError

    @abstractmethod
    def get_all_solution_versions(self, group: str, name: str) -> List[ISolution]:
        raise NotImplementedError

    @abstractmethod
    def set_catalog_id(self, catalog_id):
        raise NotImplementedError

    @abstractmethod
    def set_version(self, version):
        raise NotImplementedError

    @abstractmethod
    def get_version(self):
        raise NotImplementedError

    @abstractmethod
    def get_meta_file_path(self):
        raise NotImplementedError
