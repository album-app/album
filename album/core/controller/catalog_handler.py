from typing import List

from album.core.controller.migration_manager import MigrationManager
from album.core.controller.solution_handler import SolutionHandler
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange, ChangeType
from album.core.model.collection_index import CollectionIndex
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.resolve_operations import solution_to_group_name_version, dict_to_group_name_version
from album_runner import logging

module_logger = logging.get_active_logger

class CatalogHandler:

    def __init__(self, configuration: Configuration, collection: CollectionIndex, solution_handler: SolutionHandler):
        self.catalog_collection = collection
        self.configuration = configuration
        self.solution_handler = solution_handler
        self.migration_manager = MigrationManager()

    def create_local_catalog(self):
        catalogs = self.configuration.get_initial_catalogs()
        name = DefaultValues.local_catalog_name.value
        local_path = catalogs[name]
        self.create_new_catalog(local_path, name)

    def add_initial_catalogs(self):
        catalogs = self.configuration.get_initial_catalogs()
        for catalog in catalogs.keys():
            self.add_by_src(catalogs[catalog])

    def add_by_src(self, identifier):
        """ Adds a catalog."""
        catalog = self._create_catalog_from_src(identifier)
        if not catalog.is_cache():
            self.migration_manager.convert_catalog(catalog)
        self._add_to_index(catalog)
        self._create_catalog_cache_if_missing(catalog)
        module_logger().info('Added catalog %s!' % identifier)
        return catalog

    def _add_to_index(self, catalog: Catalog) -> int:
        catalog.catalog_id = self.catalog_collection.insert_catalog(catalog.name, str(catalog.src), str(catalog.path),
                                               int(catalog.is_deletable))
        return catalog.catalog_id

    def get_by_id(self, catalog_id):
        """Looks up a catalog by its id and returns it."""
        catalog = self.catalog_collection.get_catalog(catalog_id)
        if not catalog:
            raise LookupError("Catalog with id \"%s\" not configured!" % catalog_id)
        return self._as_catalog(catalog)

    def get_by_src(self, src):
        """Returns the catalog object of a given url if configured."""
        catalog_dict = self.catalog_collection.get_catalog_by_src(src)
        if not catalog_dict:
            raise LookupError("Catalog with src \"%s\" not configured!" % src)
        return self._as_catalog(catalog_dict)

    def get_by_name(self, name):
        """Looks up a catalog by its id and returns it."""
        catalog_dict = self.catalog_collection.get_catalog_by_name(name)
        if not catalog_dict:
            raise LookupError("Catalog with name \"%s\" not configured!" % name)
        return self._as_catalog(catalog_dict)

    def get_by_path(self, path):
        """Looks up a catalog by its id and returns it."""
        catalog_dict = self.catalog_collection.get_catalog_by_path(path)
        if not catalog_dict:
            raise LookupError("Catalog with path \"%s\" not configured!" % path)
        return self._as_catalog(catalog_dict)

    def get_all(self):
        """Creates the catalog objects from the catalogs specified in the configuration."""
        catalogs = []
        catalog_list = self.catalog_collection.get_all_catalogs()

        for catalog_entry in catalog_list:
            catalogs.append(self._as_catalog(catalog_entry))

        return catalogs

    def get_local_catalog(self):
        """Returns the first local catalog in the configuration (Reads db table from top)."""
        local_catalog = None
        for catalog in self.get_all():
            if catalog.is_local:
                local_catalog = catalog
                break

        if local_catalog is None:
            raise RuntimeError("Misconfiguration of catalogs. There must be at least one local catalog!")

        return local_catalog

    @staticmethod
    def create_new_catalog(local_path, name):
        if not local_path.exists():
            local_path.mkdir(parents=True)
        with open(local_path.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as meta:
            meta.writelines("{\"name\": \"" + name + "\", \"version\": \"" + CatalogIndex.version + "\"}")

    @staticmethod
    def _update(catalog: Catalog) -> bool:
        r = catalog.refresh_index()
        module_logger().info('Updated catalog %s!' % catalog.name)
        return r

    def update_by_name(self, catalog_name):
        catalog = self.get_by_name(catalog_name)

        return self._update(catalog)

    def update_all(self):
        catalog_r = []
        for catalog in self.get_all():
            try:
                r = self._update(catalog)
                catalog_r.append(r)
            except Exception:
                module_logger().warning("Failed to update catalog %s!" % catalog.name)
                catalog_r.append(False)
                pass

        return catalog_r

    def update_any(self, catalog_name=None):
        if catalog_name:
            self.update_by_name(catalog_name)
        else:
            self.update_all()

    def _create_catalog_from_src(self, src):
        catalog_meta_information = Catalog.retrieve_catalog_meta_information(src)
        catalog_path = self.configuration.get_cache_path_catalog(catalog_meta_information["name"])
        catalog = Catalog(None, catalog_meta_information["name"], catalog_path, src=src)
        return catalog

    @staticmethod
    def _create_catalog_cache_if_missing(catalog):
        if not catalog.path.exists():
            catalog.path.mkdir(parents=True)

    def remove_from_index_by_path(self, path):
        catalog_dict = self.catalog_collection.get_catalog_by_path(path)
        if not catalog_dict:
            module_logger().warning(f"Cannot remove catalog, catalog with path {path} not found!")
            return None

        catalog_to_remove = self._as_catalog(catalog_dict)

        if not catalog_to_remove:
            module_logger().warning("Cannot remove catalog with path \"%s\"! Not configured!" % str(path))
            return

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_entire_catalog(catalog_to_remove.catalog_id)

        return catalog_to_remove

    def remove_from_index_by_name(self, name):
        catalog_dict = self.catalog_collection.get_catalog_by_name(name)

        if not catalog_dict:
            raise LookupError("Cannot remove catalog with name \"%s\", not found!" % str(name))

        catalog_to_remove = self._as_catalog(catalog_dict)

        if not catalog_to_remove:
            raise LookupError("Cannot remove catalog with name \"%s\"! Not configured!" % str(name))

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_entire_catalog(catalog_to_remove.catalog_id)

        return catalog_to_remove

    def remove_from_index_by_src(self, src):

        catalog_to_remove = self._as_catalog(self.catalog_collection.get_catalog_by_src(src))

        if not catalog_to_remove:
            module_logger().warning("Cannot remove catalog with source \"%s\"! Not configured!" % str(src))
            return

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_entire_catalog(catalog_to_remove.catalog_id)

        return catalog_to_remove

    def get_all_as_dict(self):
        return {
            "catalogs": self.catalog_collection.get_all_catalogs()
        }

    def update_collection(self, catalog_name=None, dry_run: bool = False) -> List[CatalogUpdates]:
        if dry_run:
            if catalog_name:
                return [self._get_divergence_between_catalog_and_collection(
                    catalog_name)]
            else:
                return self._get_divergence_between_catalogs_and_collection()
        else:
            if catalog_name:
                return [self._update_collection_from_catalog(catalog_name)]
            else:
                return self._update_collection_from_catalogs()

    def _get_divergence_between_catalogs_and_collection(self) -> List[CatalogUpdates]:
        res = []
        for catalog in self.get_all():
            res.append(self._get_divergence_between_catalog_and_collection(catalog_name=catalog.name))
        return res

    def _get_divergence_between_catalog_and_collection(self, catalog_name) -> CatalogUpdates:
        catalog = self.get_by_name(catalog_name)
        res = CatalogUpdates(catalog)
        if catalog.is_cache():
            # cache catalog is always up to date since src and path are the same
            return res
        solutions_in_collection = self.catalog_collection.get_solutions_by_catalog(catalog.catalog_id)
        if not catalog.catalog_index:
            catalog.load_index()
        solutions_in_catalog = catalog.catalog_index.get_all_solutions()
        res.solution_changes = self._compare_solutions(solutions_in_collection, solutions_in_catalog)
        return res

    def _compare_solutions(self, solutions_old, solutions_new):
        res = []
        dict_old = {}
        dict_new = {}
        for solution in solutions_old:
            dict_old[solution["solution_id"]] = solution
        for solution in solutions_new:
            dict_new[solution["solution_id"]] = solution
        for solution_id in dict_old:
            solution_old = dict_old[solution_id]
            # check if solution got removed
            if solution_id not in dict_new:
                gnv = dict_to_group_name_version(solution_old)
                change = SolutionChange(gnv, ChangeType.REMOVED)
                res.append(change)
            else:
                # check if solution got changed
                if solution_old["hash"] != dict_new[solution_id]["hash"]:
                    gnv = dict_to_group_name_version(solution_old)
                    change = SolutionChange(gnv, ChangeType.CHANGED)
                    res.append(change)
        # check if solution got added
        for solution_id in dict_new:
            if solution_id not in dict_old:
                gnv = dict_to_group_name_version(dict_new[solution_id])
                change = SolutionChange(gnv, ChangeType.ADDED)
                res.append(change)
        return res

    def _update_collection_from_catalogs(self) -> List[CatalogUpdates]:
        res = []
        for catalog in self.get_all():
            res.append(self._update_collection_from_catalog(catalog_name=catalog.name))
        return res

    def _update_collection_from_catalog(self, catalog_name) -> CatalogUpdates:
        divergence = self._get_divergence_between_catalog_and_collection(catalog_name)
        #TODO apply changes to catalog attributes
        for change in divergence.solution_changes:
            self.solution_handler.apply_change(divergence.catalog, change)
        return divergence

    @staticmethod
    def _as_catalog(catalog_dict):
        return Catalog(catalog_dict['catalog_id'], catalog_dict['name'], catalog_dict['path'], catalog_dict['src'], bool(catalog_dict['deletable']))
