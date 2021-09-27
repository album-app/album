from enum import Enum
from typing import List, Optional

from album.core.model.catalog import Catalog
from album.core.model.identity import Identity


class ChangeType(Enum):
    ADDED = 1,
    REMOVED = 2,
    CHANGED = 3


class SolutionChange:
    identity: Identity
    change_type: ChangeType
    change_log: str

    def __init__(self, identity: Identity, change_type: ChangeType, change_log: Optional[str] = None):
        self.identity = identity
        self.change_type = change_type
        self.change_log = change_log

    def as_dict(self):
        return {
            "group": self.identity.group,
            "name": self.identity.name,
            "version": self.identity.version,
            "change_type": self.change_type.name,
            "change_log": self.change_log
        }


class CatalogAttributeChange:
    attribute: str
    old_value = None
    new_value = None

    def __init__(self, attribute: str, old_value, new_value):
        self.attribute = attribute
        self.old_value = old_value
        self.new_value = new_value


class CatalogUpdates:
    catalog: Catalog
    catalog_attribute_changes: List[CatalogAttributeChange] = []
    solution_changes: List[SolutionChange] = []

    def __init__(self, catalog: Catalog, solution_changes: Optional[List[CatalogAttributeChange]] = None,
                 catalog_attribute_changes: Optional[List[CatalogAttributeChange]] = None) -> None:
        if catalog_attribute_changes is None:
            catalog_attribute_changes = []
        if solution_changes is None:
            solution_changes = []
        self.catalog = catalog
        self.solution_changes = solution_changes
        self.catalog_attribute_changes = catalog_attribute_changes

    def as_dict(self):
        solution_changes_as_dict = []
        for change in self.solution_changes:
            solution_changes_as_dict.append(change.as_dict())
        return {
            "catalog": {
                "name": self.catalog.name
            },
            "solution_changes": solution_changes_as_dict
        }

    def __str__(self) -> str:
        return str(self.as_dict())


