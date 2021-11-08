import os
from pathlib import Path
from typing import List, Optional

import validators

from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange, ChangeType
from album.core.model.collection_index import CollectionIndex
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class CatalogHandler:
    """Helper class responsible for catalog handling."""
    # singletons
    migration_manager = None

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
            self.add_by_src(initial_catalogs[catalog]).dispose()

    def add_by_src(self, identifier) -> Catalog:
        """ Adds a catalog. Creates them from their src. (Git, network-drive, folder outside cache, etc.)"""
        catalog_meta_information = Catalog.retrieve_catalog_meta_information(identifier)

        catalog = self._create_catalog_from_src(identifier, catalog_meta_information)

        # always keep the local copy up to date
        if not catalog.is_cache():
            catalog_meta_information = catalog_meta_information
            self.migration_manager.migrate_catalog_index_db(
                catalog.index_path,  # the path to the catalog
                catalog_meta_information["version"],  # eventually outdated remote version
                CatalogIndex.version  # current version in the library
            )

        self._add_to_index(catalog)
        self._create_catalog_cache_if_missing(catalog)
        self.migration_manager.load_index(catalog)

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

    def get_by_id(self, catalog_id) -> Catalog:
        """Looks up a catalog by its id and returns it."""
        catalog = self.catalog_collection.get_catalog(catalog_id)
        if not catalog:
            raise LookupError("Catalog with id \"%s\" not configured!" % catalog_id)
        return self._as_catalog(catalog)

    def get_by_src(self, src) -> Catalog:
        """Returns the catalog object of a given url if configured."""
        catalog_dict = self.catalog_collection.get_catalog_by_src(src)
        if not catalog_dict:
            raise LookupError("Catalog with src \"%s\" not configured!" % src)
        return self._as_catalog(catalog_dict)

    def get_by_name(self, name) -> Catalog:
        """Looks up a catalog by its id and returns it."""
        catalog_dict = self.catalog_collection.get_catalog_by_name(name)
        if not catalog_dict:
            raise LookupError("Catalog with name \"%s\" not configured!" % name)
        return self._as_catalog(catalog_dict)

    def get_by_path(self, path) -> Catalog:
        """Looks up a catalog by its id and returns it."""
        catalog_dict = self.catalog_collection.get_catalog_by_path(path)
        if not catalog_dict:
            raise LookupError("Catalog with path \"%s\" not configured!" % path)
        return self._as_catalog(catalog_dict)

    def get_all(self) -> List[Catalog]:
        """Creates the catalog objects from the catalogs specified in the configuration."""
        catalogs = []
        catalog_list = self.catalog_collection.get_all_catalogs()

        for catalog_entry in catalog_list:
            catalogs.append(self._as_catalog(catalog_entry))

        return catalogs

    def get_local_catalog(self) -> Catalog:
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

    def _update(self, catalog: Catalog) -> bool:
        r = self.migration_manager.refresh_index(catalog)
        module_logger().info('Updated catalog %s!' % catalog.name)
        return r

    def update_by_name(self, catalog_name) -> bool:
        """Updates a catalog by its name."""
        catalog = self.get_by_name(catalog_name)

        return self._update(catalog)

    def update_all(self) -> List[bool]:
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
                return [self._get_divergence_between_catalog_and_collection(catalog_name)]
            else:
                return self._get_divergence_between_catalogs_and_collection()
        else:
            if catalog_name:
                return [self._update_collection_from_catalog(catalog_name)]
            else:
                return self._update_collection_from_catalogs()

    def _remove_from_collection(self, catalog_dict) -> Optional[Catalog]:
        try:
            catalog_to_remove = self.get_by_id(catalog_dict["catalog_id"])
        except LookupError as err:
            raise LookupError("Cannot remove catalog! Not configured...") from err

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        # todo: check for installed solutions and or parents! and fail
        self.catalog_collection.remove_catalog(catalog_to_remove.catalog_id)

        force_remove(catalog_to_remove.path)

        catalog_to_remove.dispose()

        return catalog_to_remove

    def remove_from_collection_by_path(self, path) -> Optional[Catalog]:
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

    def remove_from_collection_by_src(self, src) -> Optional[Catalog]:
        """Removes a catalog given its src from the catalog_collection."""

        if not validators.url(str(src)):
            if Path(src).exists():
                src = os.path.abspath(src)
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

    def get_all_as_dict(self) -> dict:
        """Get all catalogs as dictionary."""
        return {
            "catalogs": self.catalog_collection.get_all_catalogs()
        }

    def _create_catalog_from_src(self, src, catalog_meta_information=None) -> Catalog:
        """Creates the local cache path for a catalog given its src. (Network drive, git-link, etc.)"""
        if not catalog_meta_information:
            catalog_meta_information = Catalog.retrieve_catalog_meta_information(src)

        # the path where the catalog lives based on its metadata
        catalog_path = self.configuration.get_cache_path_catalog(catalog_meta_information["name"])

        catalog = Catalog(None, catalog_meta_information["name"], catalog_path, src=src)

        if catalog.is_local():
            catalog.src = Path(catalog.src).absolute()

        catalog.dispose()

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
        self.migration_manager.load_index(catalog)
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
    def _compare_solutions(solutions_old, solutions_new) -> List[SolutionChange]:
        res = []
        # CAUTION: solutions should not be compared based on their id as this might change

        dict_old_coordinates = {}
        list_old_hash = list([s["hash"] for s in solutions_old])
        for s in solutions_old:
            dict_old_coordinates[dict_to_coordinates(s)] = s

        dict_new_coordinates = {}
        dict_new_hash = {}
        for s in solutions_new:
            dict_new_coordinates[dict_to_coordinates(s)] = s
            dict_new_hash[s["hash"]] = s

        for hash in dict_new_hash.keys():
            # get metadata
            coordinates = dict_to_coordinates(dict_new_hash[hash])

            # solution updated or added
            if hash not in list_old_hash:
                if coordinates in dict_old_coordinates.keys():  # changed when metadata in old solution list
                    change = SolutionChange(coordinates, ChangeType.CHANGED)
                    res.append(change)

                    # remove solution from old coordinates list
                    # for later iteration over this list to determine deleted solutions
                    dict_old_coordinates.pop(coordinates)

                else:  # added when metadata not in old solution list
                    change = SolutionChange(coordinates, ChangeType.ADDED)
                    res.append(change)
            else:  # not changed
                dict_old_coordinates.pop(coordinates)

        # iterate over remaining solutions in dict_old_coordinates. These are the removed solutions
        for coordinates in dict_old_coordinates.keys():
            change = SolutionChange(coordinates, ChangeType.REMOVED)
            res.append(change)

        return res

    @staticmethod
    def _as_catalog(catalog_dict) -> Catalog:
        return Catalog(
            catalog_dict['catalog_id'],
            catalog_dict['name'],
            catalog_dict['path'],
            catalog_dict['src'],
            bool(catalog_dict['deletable'])
        )
