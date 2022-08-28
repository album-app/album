from abc import abstractmethod, ABCMeta
from typing import Optional, List

from album.core.api.model.database import IDatabase
from album.runner.core.api.model.coordinates import ICoordinates


class ICollectionIndex(IDatabase):
    __metaclass__ = ABCMeta

    class ICollectionSolution:
        __metaclass__ = ABCMeta

        @abstractmethod
        def setup(self) -> dict:
            raise NotImplementedError

        def internal(self) -> dict:
            raise NotImplementedError

    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def update_name_version(self, name: str, version: str, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_name(self, close: bool = True) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_version(self, close: bool = True) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_empty(self, close: bool = True) -> bool:
        raise NotImplementedError

    @abstractmethod
    def insert_catalog(
        self, name, src, path, deletable, branch_name, catalog_type, close: bool = True
    ):
        raise NotImplementedError

    @abstractmethod
    def get_catalog(self, catalog_id, close: bool = True) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_catalog_by_name(self, catalog_name: str, close: bool = True) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_catalog_by_path(self, catalog_path: str, close: bool = True) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_catalog_by_src(self, catalog_src: str, close: bool = True) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_all_catalogs(self, close: bool = True) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def remove_catalog(self, catalog_id, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def insert_solution(self, catalog_id, solution_attrs, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def get_all_solutions(self, close: bool = True) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_all_installed_solutions_by_catalog(
        self, catalog_id, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_catalog(
        self, catalog_id, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_hash(
        self, hash_value, close: bool = True
    ) -> Optional[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_collection_id(
        self, collection_id, close: bool = True
    ) -> Optional[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_doi(
        self, doi, close: bool = True
    ) -> Optional[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solution_by_catalog_grp_name_version(
        self, catalog_id, coordinates: ICoordinates, close: bool = True
    ) -> Optional[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_grp_name_version(
        self, coordinates: ICoordinates, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_name_version(
        self, name: str, version: str, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_grp_name(
        self, group: str, name: str, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_solutions_by_name(
        self, name: str, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_recently_installed_solutions(
        self, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_recently_launched_solutions(
        self, close: bool = True
    ) -> List[ICollectionSolution]:
        raise NotImplementedError

    @abstractmethod
    def get_unfinished_installation_solutions(self, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def update_solution(
        self,
        catalog_id,
        coordinates: ICoordinates,
        solution_attrs: dict,
        supported_attrs: list,
        close: bool = True,
    ):
        raise NotImplementedError

    @abstractmethod
    def add_or_replace_solution(
        self, catalog_id, coordinates: ICoordinates, solution_attrs, close: bool = True
    ):
        raise NotImplementedError

    @abstractmethod
    def remove_solution(
        self, catalog_id, coordinates: ICoordinates, close: bool = True
    ):
        raise NotImplementedError

    @abstractmethod
    def is_installed(self, catalog_id, coordinates: ICoordinates, close: bool = True):
        raise NotImplementedError

    @abstractmethod
    def insert_collection_collection(
        self,
        collection_id_parent,
        collection_id_child,
        catalog_id_parent,
        catalog_id_child,
        close=True,
    ):
        raise NotImplementedError

    @abstractmethod
    def remove_parent(self, collection_id, close=True):
        raise NotImplementedError
