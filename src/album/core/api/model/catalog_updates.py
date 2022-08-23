from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import List

from album.core.api.model.catalog import ICatalog
from album.runner.core.api.model.coordinates import ICoordinates


class ChangeType(Enum):
    ADDED = (1,)
    REMOVED = (2,)
    CHANGED = 3


class ISolutionChange:
    __metaclass__ = ABCMeta

    @abstractmethod
    def coordinates(self) -> ICoordinates:
        raise NotImplementedError

    @abstractmethod
    def change_type(self) -> ChangeType:
        raise NotImplementedError

    @abstractmethod
    def change_log(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def solution_status(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def as_dict(self) -> dict:
        raise NotImplementedError


class ICatalogAttributeChange:
    __metaclass__ = ABCMeta

    @abstractmethod
    def old_value(self):
        raise NotImplementedError

    @abstractmethod
    def new_value(self):
        raise NotImplementedError

    @abstractmethod
    def attribute(self) -> str:
        raise NotImplementedError


class ICatalogUpdates:
    __metaclass__ = ABCMeta

    @abstractmethod
    def catalog(self) -> ICatalog:
        raise NotImplementedError

    @abstractmethod
    def catalog_attribute_changes(self) -> List[ICatalogAttributeChange]:
        raise NotImplementedError

    @abstractmethod
    def solution_changes(self) -> List[ISolutionChange]:
        raise NotImplementedError

    @abstractmethod
    def as_dict(self) -> dict:
        raise NotImplementedError
