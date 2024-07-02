"""This module contains the interface for the Catalog class."""
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution
from git import Repo

from album.core.api.model.catalog_index import ICatalogIndex


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
        """Get the id of the catalog in the database."""
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """Get the name of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def src(self) -> str:
        """Get the source of the catalog. Gitlab/github link or path."""
        raise NotImplementedError

    @abstractmethod
    def version(self) -> str:
        """Get the version of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def index(self) -> Optional[ICatalogIndex]:
        """Get the index of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def path(self) -> Path:
        """Get the path to the catalog cache."""
        raise NotImplementedError

    @abstractmethod
    def branch_name(self) -> str:
        """Get the branch name of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def is_deletable(self) -> bool:
        """Check if the catalog is deletable."""
        raise NotImplementedError

    @abstractmethod
    def is_cache(self) -> bool:
        """Check if the catalog is cached."""
        raise NotImplementedError

    @abstractmethod
    def is_local(self) -> bool:
        """Check if the catalog is local."""
        raise NotImplementedError

    @abstractmethod
    def load_index(self) -> None:
        """Load the catalog index."""
        raise NotImplementedError

    @abstractmethod
    def solution_list_path(self) -> Path:
        """Get the path to the catalog solution list cache."""
        raise NotImplementedError

    @abstractmethod
    def index_file_path(self) -> Path:
        """Get the path to the catalog index cache."""
        raise NotImplementedError

    @abstractmethod
    def set_index_path(self, path: Path) -> None:
        """Set the path to the catalog index cache."""
        raise NotImplementedError

    @abstractmethod
    def type(self) -> str:
        """Get the type of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def dispose(self) -> None:
        """Dispose the catalog."""
        raise NotImplementedError

    @abstractmethod
    def update_index_cache_if_possible(self, tmp_dir: str) -> bool:
        """Update the index cache if possible."""
        raise NotImplementedError

    @abstractmethod
    def update_index_cache(self, tmp_dir: str) -> bool:
        """Update the index cache."""
        raise NotImplementedError

    @abstractmethod
    def add(self, active_solution: ISolution, force_overwrite: bool = False) -> None:
        """Add a solution to the catalog."""
        raise NotImplementedError

    @abstractmethod
    def remove(self, coordinates: ICoordinates) -> None:
        """Remove a solution from the catalog."""
        raise NotImplementedError

    @contextmanager
    def retrieve_catalog(
        self,
        path: Union[Path, None] = None,
        force_retrieve: bool = False,
        update: bool = True,
    ) -> Generator[Repo, None, None]:
        """Retrieve the catalog."""
        yield
        raise NotImplementedError

    @abstractmethod
    def get_meta_information(self) -> Dict[str, str]:
        """Get the meta information of the catalog."""
        raise NotImplementedError

    @abstractmethod
    def get_all_solution_versions(self, group: str, name: str) -> List[ISolution]:
        """Get all solution versions."""
        raise NotImplementedError

    @abstractmethod
    def set_catalog_id(self, catalog_id: int) -> None:
        """Set the catalog id."""
        raise NotImplementedError

    @abstractmethod
    def set_version(self, version: str) -> None:
        """Set the version."""
        raise NotImplementedError

    @abstractmethod
    def get_version(self) -> str:
        """Get the version."""
        raise NotImplementedError

    @abstractmethod
    def get_meta_file_path(self) -> Path:
        """Get the meta file path."""
        raise NotImplementedError
