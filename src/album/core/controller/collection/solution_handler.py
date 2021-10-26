from datetime import datetime

from album.core import Solution
from album.core.model.catalog import Catalog
from album.core.model.catalog_updates import ChangeType, SolutionChange
from album.core.model.collection_index import CollectionIndex
from album.core.model.coordinates import Coordinates
from album.core.utils.operations.file_operations import copy_folder
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class SolutionHandler:
    """Handles everything inside the Collection responsible for a solution entry.

    Is NOT responsible for resolving paths as this is part of a catalog.
    """

    def __init__(self, collection: CollectionIndex):
        self.catalog_collection = collection

    def add_or_replace(self, catalog: Catalog, active_solution: Solution, path):
        deploy_dict = active_solution.get_deploy_dict()
        self.catalog_collection.add_or_replace_solution(
            catalog.catalog_id,
            active_solution.coordinates,
            deploy_dict
        )
        # get the install location
        install_location = catalog.get_solution_path(dict_to_coordinates(deploy_dict))

        copy_folder(path, install_location, copy_root_folder=False)

    def set_uninstalled(self, catalog: Catalog, coordinates: Coordinates):
        self.update_solution(catalog, coordinates, {"installed": 0})

    def set_parent(self, catalog_parent: Catalog, catalog_child: Catalog, coordinates_parent: Coordinates,
                   coordinates_child: Coordinates):

        # retrieve parent entry
        parent_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog_parent.catalog_id, coordinates_parent, close=False
        )
        # retrieve child entry
        child_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog_child.catalog_id, coordinates_child, close=False
        )

        self.catalog_collection.insert_solution_solution(
            parent_entry["collection_id"],
            child_entry["collection_id"],
            catalog_parent.catalog_id,
            catalog_child.catalog_id
        )

    def remove_solution(self, catalog: Catalog, coordinates: Coordinates):
        self.catalog_collection.remove_solution(catalog.catalog_id, coordinates)

    def update_solution(self, catalog: Catalog, coordinates: Coordinates, attrs):
        self.catalog_collection.update_solution(catalog.catalog_id, coordinates, attrs, self.get_solution_keys())

    @staticmethod
    def get_solution_keys():
        keys = Solution.deploy_keys.copy()
        # keys in a separate column
        keys.remove("authors")
        keys.remove("tags")
        keys.remove("args")
        keys.remove("cite")
        keys.remove("covers")
        # keys to allow to be set
        keys.append("hash")
        keys.append("installed")
        keys.append("install_date")
        return keys

    def apply_change(self, catalog, change: SolutionChange):
        # FIXME handle other tables (tags etc)
        if change.change_type is ChangeType.ADDED:
            self.catalog_collection.add_or_replace_solution(
                catalog.catalog_id,
                change.coordinates,
                catalog.catalog_index.get_solution_by_coordinates(change.coordinates)
            )

        elif change.change_type is ChangeType.REMOVED:
            self.remove_solution(catalog, change.coordinates)

        elif change.change_type is ChangeType.CHANGED:
            self.remove_solution(catalog, change.coordinates)
            self.catalog_collection.add_or_replace_solution(
                catalog.catalog_id,
                change.coordinates,
                catalog.catalog_index.get_solution_by_coordinates(change.coordinates)
            )

    def set_installed(self, catalog: Catalog, coordinates: Coordinates):
        self.update_solution(catalog, coordinates, {"installed": 1, "install_date": datetime.now().isoformat()})

    def is_installed(self, catalog: Catalog, coordinates: Coordinates) -> bool:
        return self.catalog_collection.is_installed(catalog.catalog_id, coordinates)
