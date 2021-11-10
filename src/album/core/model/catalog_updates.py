from enum import Enum
from typing import List, Optional

from album.core.model.catalog import Catalog
from album.core.model.coordinates import Coordinates


class ChangeType(Enum):
    ADDED = 1,
    REMOVED = 2,
    CHANGED = 3


class SolutionChange:
    coordinates: Coordinates
    change_type: ChangeType
    change_log: str

    def __init__(self, coordinates: Coordinates, change_type: ChangeType, change_log: Optional[str] = None):
        self.coordinates = coordinates
        self.change_type = change_type
        self.change_log = change_log

    def __eq__(self, other):
        return isinstance(other, SolutionChange) \
               and other.coordinates == self.coordinates \
               and other.change_type == self.change_type \
               and other.change_log == self.change_log

    def as_dict(self):
        return {
            "group": self.coordinates.group,
            "name": self.coordinates.name,
            "version": self.coordinates.version,
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

    def get_cmdline_info(self) -> str:
        res = 'Catalog: %s\n' % self.catalog.name
        if len(self.catalog_attribute_changes) > 0:
            res += '  Catalog attribute changes:\n'
            for item in self.catalog_attribute_changes:
                res += '  name: %s, new value: %s\n' % (item.attribute, item.new_value)
        if len(self.solution_changes) > 0:
            res += '  Catalog solution changes:\n'
            for i, item in enumerate(self.solution_changes):
                if i is len(self.solution_changes) - 1:
                    res += '  └─ [%s] %s\n' % (item.change_type.name, item.coordinates)
                    separator = ' '
                else:
                    res += '  ├─ [%s] %s\n' % (item.change_type.name, item.coordinates)
                    separator = '|'
                res += '  %s     %schangelog: %s\n' % (
                    separator, (" " * len(item.change_type.name)), item.change_log)

        if len(self.catalog_attribute_changes) == 0 and len(self.solution_changes) == 0:
            res += '  No changes.\n'

        return res

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
