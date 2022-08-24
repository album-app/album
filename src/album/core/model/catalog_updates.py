from typing import List, Optional

from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_updates import (
    ISolutionChange,
    ChangeType,
    ICatalogAttributeChange,
    ICatalogUpdates,
)
from album.runner.core.api.model.coordinates import ICoordinates


class SolutionChange(ISolutionChange):
    def __init__(
        self,
        coordinates: ICoordinates,
        change_type: ChangeType,
        change_log: Optional[str] = None,
        solution_status: Optional[dict] = None,
    ):
        self._coordinates = coordinates
        self._change_type = change_type
        self._change_log = change_log
        self._solution_status = solution_status

    def __eq__(self, other):
        return (
            isinstance(other, ISolutionChange)
            and other.coordinates() == self._coordinates
            and other.change_type() == self._change_type
            and other.change_log() == self._change_log
            and other.solution_status() == self._solution_status
        )

    def as_dict(self):
        return {
            "group": self._coordinates.group(),
            "name": self._coordinates.name(),
            "version": self._coordinates.version(),
            "change_type": self._change_type.name,
            "change_log": self._change_log,
            # solution status only internal
        }

    def coordinates(self) -> ICoordinates:
        return self._coordinates

    def change_type(self) -> ChangeType:
        return self._change_type

    def change_log(self) -> str:
        return self._change_log

    def solution_status(self) -> dict:
        return self._solution_status


class CatalogAttributeChange(ICatalogAttributeChange):
    def __init__(self, attribute: str, old_value, new_value):
        self._attribute = attribute
        self._old_value = old_value
        self._new_value = new_value

    def old_value(self):
        return self._old_value

    def new_value(self):
        return self._new_value

    def attribute(self) -> str:
        return self._attribute


class CatalogUpdates(ICatalogUpdates):
    _catalog: ICatalog
    _catalog_attribute_changes: List[ICatalogAttributeChange] = []
    _solution_changes: List[ISolutionChange] = []

    def __init__(
        self,
        catalog: ICatalog,
        solution_changes: Optional[List[ISolutionChange]] = None,
        catalog_attribute_changes: Optional[List[ICatalogAttributeChange]] = None,
    ) -> None:
        if catalog_attribute_changes is None:
            catalog_attribute_changes = []
        if solution_changes is None:
            solution_changes = []
        self._catalog = catalog
        self._solution_changes = solution_changes
        self._catalog_attribute_changes = catalog_attribute_changes

    def as_dict(self):
        solution_changes_as_dict = []
        for change in self._solution_changes:
            solution_changes_as_dict.append(change.as_dict())
        return {
            "catalog": {"name": self._catalog.name()},
            "solution_changes": solution_changes_as_dict,
        }

    def __str__(self) -> str:
        return str(self.as_dict())

    def catalog(self) -> ICatalog:
        return self._catalog

    def catalog_attribute_changes(self) -> List[ICatalogAttributeChange]:
        return self._catalog_attribute_changes

    def solution_changes(self):
        return self._solution_changes
