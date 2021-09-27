from pathlib import Path
from typing import List, Optional

import validators
from album.core.utils.operations.file_operations import force_remove

from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange, ChangeType
from album.core.model.collection_index import CollectionIndex
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.resolve_operations import dict_to_identity
from album_runner import logging

module_logger = logging.get_active_logger


class CatalogHandler:
    """Helper class responsible for catalog handling."""

    def __init__(self, configuration: Configuration, collection: CollectionIndex, solution_handler: SolutionHandler):
        self.catalog_collection = collection
        self.configuration = configuration
        self.solution_handler = solution_handler
        self.migration_manager = MigrationManager()

    def create_local_catalog(self):
        """Creates the local catalog on the disk from the available initial catalogs.

         Does not contain a DB file. Used only when album starts the first time.

         """
        initial_catalogs = self.configuration.get_initial_catalogs()
        name = DefaultValues.local_catalog_name.value
        local_path = initial_catalogs[name]
        self.create_new_catalog(local_path, name)

    def add_initial_catalogs(self):
        """Adds the initial catalogs to the catalog_collection.

        Copies/downloads them from their src to their local cache. (Except local_catalog)

        """
        initial_catalogs = self.configuration.get_initial_catalogs()
        for catalog in initial_catalogs.keys():
            self.add_by_src(initial_catalogs[catalog])

    def add_by_src(self, identifier):
        """ Adds a catalog. Creates them from their src. (Git, network-drive, folder outside cache, etc.)"""
        catalog = self._create_catalog_from_src(identifier)

        # always keep the local copy up to date
        if not catalog.is_cache():
            catalog_meta_information = Catalog.retrieve_catalog_meta_information(catalog.src)
            self.migration_manager.migrate_catalog_index_db(
                catalog.index_path,
                catalog_meta_information["version"],
                CatalogIndex.version
            )

        self._add_to_index(catalog)
        self._create_catalog_cache_if_missing(catalog)

        module_logger().info('Added catalog %s!' % identifier)
        return catalog

    def _add_to_index(self, catalog: Catalog) -> int:
        """ Adds a catalog to the collection index.

        Args:
            catalog: The catalog object

        Returns:
            The database ID of the catalog.

        """
        catalog.catalog_id = self.catalog_collection.insert_catalog(
            catalog.name,
            str(catalog.src),
            str(catalog.path),
            int(catalog.is_deletable)
        )
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
        """Creates the meta-file for a new catalog on the disk."""
        if not local_path.exists():
            local_path.mkdir(parents=True)
        with open(local_path.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as meta:
            meta.writelines("{\"name\": \"" + name + "\", \"version\": \"" + CatalogIndex.version + "\"}")

    @staticmethod
    def _update(catalog: Catalog) -> bool:
        # TODO call migration manager
        r = catalog.refresh_index()
        module_logger().info('Updated catalog %s!' % catalog.name)
        return r

    def update_by_name(self, catalog_name):
        """Updates a catalog by its name."""
        catalog = self.get_by_name(catalog_name)

        return self._update(catalog)

    def update_all(self):
        """Updates all available catalogs"""
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
        """Updates either all catalogs or one by its name."""
        if catalog_name:
            self.update_by_name(catalog_name)
        else:
            self.update_all()

    def update_collection(self, catalog_name=None, dry_run: bool = False) -> List[CatalogUpdates]:
        """Includes all new changes from a given catalog (or all catalogs) in the catalog_collection."""
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

    def _remove_from_collection(self, catalog_dict):
        catalog_to_remove = self._as_catalog(catalog_dict)

        if not catalog_to_remove:
            raise LookupError("Cannot remove catalog! Not configured...")

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_catalog(catalog_to_remove.catalog_id)

        force_remove(catalog_to_remove.path)

        return catalog_to_remove

    def remove_from_collection_by_path(self, path):
        """Removes a catalog given by its path from the catalog_collection.

        Thereby deleting all its entries from the collection.

        """
        catalog_dict = self.catalog_collection.get_catalog_by_path(path)

        if not catalog_dict:
            module_logger().warning("Cannot remove catalog, catalog with path %s not found!" % str(path))
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with path %s." % str(path))

        return catalog_to_remove

    def remove_from_collection_by_name(self, name) -> Optional[Catalog]:
        """Removes a catalog given its name from the catalog_collection."""
        catalog_dict = self.catalog_collection.get_catalog_by_name(name)

        if not catalog_dict:
            module_logger().warning("Cannot remove catalog, catalog with name \"%s\", not found!" % str(name))
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with name %s." % str(name))

        return catalog_to_remove

    def remove_from_collection_by_src(self, src):
        """Removes a catalog given its src from the catalog_collection."""

        if not validators.url(str(src)):
            if Path(src).exists():
                src = str(Path(src).absolute())
            else:
                module_logger().warning("Cannot remove catalog with source \"%s\"! Not configured!" % str(src))
                return None

        catalog_dict = self.catalog_collection.get_catalog_by_src(src)

        if not catalog_dict:
            module_logger().warning("Cannot remove catalog with source \"%s\"! Not configured!" % str(src))
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with source %s" % str(src))

        return catalog_to_remove

    def get_all_as_dict(self):
        """Get all catalogs as dictionary."""
        return {
            "catalogs": self.catalog_collection.get_all_catalogs()
        }

    def _create_catalog_from_src(self, src):
        """Creates the local cache path for a catalog given its src. (Network drive, git-link, etc.)"""
        catalog_meta_information = Catalog.retrieve_catalog_meta_information(src)
        catalog_path = self.configuration.get_cache_path_catalog(catalog_meta_information["name"])
        catalog = Catalog(None, catalog_meta_information["name"], catalog_path, src=src)
        if catalog.is_local():
            catalog.src = Path(catalog.src).absolute()
        return catalog

    @staticmethod
    def _create_catalog_cache_if_missing(catalog):
        """Creates the path of a catalog if it is missing."""
        if not catalog.path.exists():
            catalog.path.mkdir(parents=True)

    def _get_divergence_between_catalogs_and_collection(self) -> List[CatalogUpdates]:
        """Gets the divergence list between all catalogs and the catalog_collection."""
        res = []
        for catalog in self.get_all():
            res.append(self._get_divergence_between_catalog_and_collection(catalog_name=catalog.name))
        return res

    def _get_divergence_between_catalog_and_collection(self, catalog_name) -> CatalogUpdates:
        """Gets the divergence between a given catalog and the catalog_collection"""
        catalog = self.get_by_name(catalog_name)
        res = CatalogUpdates(catalog)
        if catalog.is_cache():
            # cache catalog is always up to date since src and path are the same
            return res
        solutions_in_collection = self.catalog_collection.get_solutions_by_catalog(catalog.catalog_id)
        catalog.load_index()
        solutions_in_catalog = catalog.catalog_index.get_all_solutions()
        res.solution_changes = self._compare_solutions(solutions_in_collection, solutions_in_catalog)
        return res

    def _update_collection_from_catalogs(self) -> List[CatalogUpdates]:
        res = []
        for catalog in self.get_all():
            res.append(self._update_collection_from_catalog(catalog_name=catalog.name))
        return res

    def _update_collection_from_catalog(self, catalog_name) -> CatalogUpdates:
        divergence = self._get_divergence_between_catalog_and_collection(catalog_name)
        # TODO apply changes to catalog attributes
        for change in divergence.solution_changes:
            self.solution_handler.apply_change(divergence.catalog, change)
        return divergence

    @staticmethod
    def _compare_solutions(solutions_old, solutions_new):
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
                identity = dict_to_identity(solution_old)
                change = SolutionChange(identity, ChangeType.REMOVED)
                res.append(change)
            else:
                # check if solution got changed
                if solution_old["hash"] != dict_new[solution_id]["hash"]:
                    identity = dict_to_identity(solution_old)
                    change = SolutionChange(identity, ChangeType.CHANGED)
                    res.append(change)
        # check if solution got added
        for solution_id in dict_new:
            if solution_id not in dict_old:
                identity = dict_to_identity(dict_new[solution_id])
                change = SolutionChange(identity, ChangeType.ADDED)
                res.append(change)
        return res

    @staticmethod
    def _as_catalog(catalog_dict):
        return Catalog(catalog_dict['catalog_id'], catalog_dict['name'], catalog_dict['path'], catalog_dict['src'],
                       bool(catalog_dict['deletable']))
