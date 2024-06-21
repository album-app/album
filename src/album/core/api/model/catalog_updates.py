"""Module for the catalog updates models."""
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.model.catalog import ICatalog


class ChangeType(Enum):
    """Enum for the type of change."""

    ADDED = (1,)
    REMOVED = (2,)
    CHANGED = 3


class ISolutionChange:
    """Interface for a solution change."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def coordinates(self) -> ICoordinates:
        """Return the coordinates of the solution affected by the change."""
        raise NotImplementedError

    @abstractmethod
    def change_type(self) -> ChangeType:
        """Return the type of change."""
        raise NotImplementedError

    @abstractmethod
    def change_log(self) -> Optional[str]:
        """Return the change log."""
        raise NotImplementedError

    @abstractmethod
    def solution_status(self) -> Optional[Dict[str, Any]]:
        """Return the status of the solution."""
        raise NotImplementedError

    @abstractmethod
    def as_dict(self) -> Dict[str, Any]:
        """Return the solution change as a dictionary."""
        raise NotImplementedError


class ICatalogAttributeChange:
    """Interface for a catalog attribute change."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def old_value(self) -> str:
        """Return the old value of the attribute."""
        raise NotImplementedError

    @abstractmethod
    def new_value(self) -> str:
        """Return the new value of the attribute."""
        raise NotImplementedError

    @abstractmethod
    def attribute(self) -> str:
        """Return the attribute affected by the change."""
        raise NotImplementedError


class ICatalogUpdates:
    """Interface for catalog updates."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def catalog(self) -> ICatalog:
        """Return the catalog affected by the change."""
        raise NotImplementedError

    @abstractmethod
    def catalog_attribute_changes(self) -> List[ICatalogAttributeChange]:
        """Return the catalog attribute changes."""
        raise NotImplementedError

    @abstractmethod
    def solution_changes(self) -> List[ISolutionChange]:
        """Return the solution changes."""
        raise NotImplementedError

    @abstractmethod
    def as_dict(self) -> Dict[str, Any]:
        """Return the catalog updates as a dictionary."""
        raise NotImplementedError
