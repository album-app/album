import os
from pathlib import Path
from typing import List, Optional, Dict

import validators

from album.core.api.album import IAlbum
from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.model.catalog import ICatalog
from album.core.model.catalog import Catalog, get_index_url, get_index_dir
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange, ChangeType
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove, copy, get_dict_from_json
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.url_operations import download_resource
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class CatalogHandler(ICatalogHandler):
    """Helper class responsible for catalog handling."""

    def __init__(self, album: IAlbum):
        self.album = album

    def create_local_catalog(self):
        initial_catalogs = self.album.configuration().get_initial_catalogs()
        name = DefaultValues.local_catalog_name.value
        local_path = initial_catalogs[name]
        self.create_new_catalog(local_path, name)

    def add_initial_catalogs(self):
        self.create_local_catalog()
        initial_catalogs = self.album.configuration().get_initial_catalogs()
        initial_catalogs_branch_name = self.album.configuration().get_initial_catalogs_branch_name()
        for catalog in initial_catalogs.keys():
            self.add_by_src(str(initial_catalogs[catalog]), initial_catalogs_branch_name[catalog]).dispose()

    def add_by_src(self, identifier, branch_name="main") -> Catalog:
        identifier = str(identifier)
        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_src(identifier)
        if catalog_dict:
            module_logger().warning("Cannot add catalog twice! Doing nothing...")
            return self._as_catalog(catalog_dict)
        else:
            catalog_meta_information = self._retrieve_catalog_meta_information(identifier, branch_name)

            catalog = self._create_catalog_from_src(identifier, catalog_meta_information, branch_name)

            # always keep the local copy up to date
            if not catalog.is_cache():
                catalog_meta_information = catalog_meta_information
                self.album.migration_manager().migrate_catalog_index_db(
                    catalog.index_path(),  # the path to the catalog
                    catalog_meta_information["version"],  # eventually outdated remote version
                    CatalogIndex.version  # current version in the library
                )

            self._add_to_index(catalog)
            self._create_catalog_cache_if_missing(catalog)
            self.album.migration_manager().load_index(catalog)

            module_logger().info('Added catalog %s!' % identifier)
            return catalog

    def _add_to_index(self, catalog: ICatalog) -> int:
        catalog_id = self.album.collection_manager().get_collection_index().insert_catalog(
            catalog.name(),
            str(catalog.src()),
            str(catalog.path()),
            int(catalog.is_deletable()),
            str(catalog.branch_name())
        )
        catalog.set_catalog_id(catalog_id)
        return catalog.catalog_id()

    def get_by_id(self, catalog_id) -> Catalog:
        catalog = self.album.collection_manager().get_collection_index().get_catalog(catalog_id)
        if not catalog:
            raise LookupError("Catalog with id \"%s\" not configured!" % catalog_id)
        return self._as_catalog(catalog)

    def get_by_src(self, src) -> Catalog:
        src = str(src)
        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_src(src)
        if not catalog_dict:
            raise LookupError("Catalog with src \"%s\" not configured!" % src)
        return self._as_catalog(catalog_dict)

    def get_by_name(self, name) -> Catalog:
        """Looks up a catalog by its id and returns it."""
        name = str(name)
        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_name(name)
        if not catalog_dict:
            raise LookupError("Catalog with name \"%s\" not configured!" % name)
        return self._as_catalog(catalog_dict)

    def get_by_path(self, path) -> Catalog:
        path = str(path)
        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_path(path)
        if not catalog_dict:
            raise LookupError("Catalog with path \"%s\" not configured!" % path)
        return self._as_catalog(catalog_dict)

    def get_all(self) -> List[Catalog]:
        catalogs = []
        catalog_list = self.album.collection_manager().get_collection_index().get_all_catalogs()

        for catalog_entry in catalog_list:
            catalogs.append(self._as_catalog(catalog_entry))

        return catalogs

    def get_local_catalog(self) -> Catalog:
        local_catalog = None
        for catalog in self.get_all():
            if catalog.is_local:
                local_catalog = catalog
                break

        if local_catalog is None:
            raise RuntimeError("Misconfiguration of catalogs. There must be at least one local catalog!")

        return local_catalog

    def create_new(self, local_path, name):
        CatalogHandler.create_new_catalog(local_path, name)

    @staticmethod
    def create_new_catalog(local_path, name):
        """Creates the meta-file for a new catalog on the disk."""
        if not local_path.exists():
            local_path.mkdir(parents=True)
        with open(local_path.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as meta:
            meta.writelines("{\"name\": \"" + name + "\", \"version\": \"" + CatalogIndex.version + "\"}")

    def _update(self, catalog: Catalog) -> bool:
        r = self.album.migration_manager().refresh_index(catalog)
        module_logger().info('Updated catalog %s!' % catalog.name())
        return r

    def update_by_name(self, catalog_name) -> bool:
        catalog = self.get_by_name(catalog_name)

        return self._update(catalog)

    def update_all(self) -> List[bool]:
        catalog_r = []
        for catalog in self.get_all():
            try:
                r = self._update(catalog)
                catalog_r.append(r)
            except Exception:
                module_logger().warning("Failed to update catalog %s!" % catalog.name())
                catalog_r.append(False)
                pass

        return catalog_r

    def update_any(self, catalog_name=None):
        if catalog_name:
            self.update_by_name(catalog_name)
        else:
            self.update_all()

    def update_collection(self, catalog_name=None, dry_run: bool = False) -> Dict[str, CatalogUpdates]:
        if dry_run:
            if catalog_name:
                return {catalog_name: self._get_divergence_between_catalog_and_collection(catalog_name)}
            else:
                return self._get_divergence_between_catalogs_and_collection()
        else:
            if catalog_name:
                return {catalog_name: self._update_collection_from_catalog(catalog_name)}
            else:
                return self._update_collection_from_catalogs()

    def _remove_from_collection(self, catalog_dict) -> Optional[Catalog]:
        try:
            catalog_to_remove = self.get_by_id(catalog_dict["catalog_id"])
        except LookupError as err:
            raise LookupError("Cannot remove catalog! Not configured...") from err

        if not catalog_to_remove.is_deletable():
            raise AttributeError("Cannot remove catalog! Marked as not deletable!")

        installed_solutions = self.get_installed_solutions(catalog_to_remove)

        if installed_solutions:
            installed_solutions_string = ", ".join([str(dict_to_coordinates(i.setup())) for i in installed_solutions])
            raise RuntimeError(
                "Cannot remove catalog! "
                "Has the following solutions installed: %s" % installed_solutions_string
            )

        self.album.collection_manager().get_collection_index().remove_catalog(catalog_to_remove.catalog_id())

        force_remove(catalog_to_remove.path())

        catalog_to_remove.dispose()

        return catalog_to_remove

    def remove_from_collection_by_path(self, path) -> Optional[Catalog]:
        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_path(path)

        if not catalog_dict:
            module_logger().warning("Cannot remove catalog, catalog with path %s not found!" % str(path))
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with path %s." % str(path))

        return catalog_to_remove

    def remove_from_collection_by_name(self, name) -> Optional[Catalog]:
        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_name(name)

        if not catalog_dict:
            module_logger().warning("Cannot remove catalog, catalog with name \"%s\", not found!" % str(name))
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with name %s." % str(name))

        return catalog_to_remove

    def remove_from_collection_by_src(self, src) -> Optional[Catalog]:
        if not validators.url(str(src)):
            if Path(src).exists():
                src = os.path.abspath(src)
            else:
                module_logger().warning("Cannot remove catalog with source \"%s\"! Not configured!" % str(src))
                return None

        catalog_dict = self.album.collection_manager().get_collection_index().get_catalog_by_src(src)

        if not catalog_dict:
            module_logger().warning("Cannot remove catalog with source \"%s\"! Not configured!" % str(src))
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with source %s" % str(src))

        return catalog_to_remove

    def get_installed_solutions(self, catalog: ICatalog):
        installed_solutions = self.album.collection_manager().get_collection_index().get_all_installed_solutions_by_catalog(
            catalog.catalog_id()
        )
        return installed_solutions

    def get_all_as_dict(self) -> dict:
        return {
            "catalogs": self.album.collection_manager().get_collection_index().get_all_catalogs()
        }

    def set_version(self, catalog: ICatalog):
        database_version = catalog.index().get_version()
        meta_dict = self._retrieve_catalog_meta_information(catalog.path(), catalog.branch_name())
        if meta_dict:
            meta_version = meta_dict['version']
        else:
            raise ValueError("Catalog meta information cannot be found! Refresh the catalog!")

        if database_version != meta_version:
            raise ValueError(
                f"Catalog meta information (version {meta_version}) unequal to actual version {database_version}!")

        catalog.set_version(database_version)
        return database_version

    def _retrieve_catalog_meta_information(self, identifier, branch_name="main"):
        if validators.url(str(identifier)):
            _, meta_src = get_index_url(identifier, branch_name)
            meta_file = download_resource(
                meta_src, self.album.configuration().cache_path_download().joinpath(
                    DefaultValues.catalog_index_metafile_json.value)
            )
        elif Path(identifier).exists():
            _, meta_src = get_index_dir(identifier)
            if meta_src.exists():
                meta_file = copy(
                    meta_src,
                    self.album.configuration().cache_path_download().joinpath(
                        DefaultValues.catalog_index_metafile_json.value)
                )
            else:
                raise FileNotFoundError("Cannot retrieve meta information for the catalog!")
        else:
            raise RuntimeError("Cannot retrieve meta information for the catalog!")

        meta_dict = get_dict_from_json(meta_file)

        return meta_dict

    def _create_catalog_from_src(self, src, catalog_meta_information=None, branch_name="main") -> Catalog:
        """Creates the local cache path for a catalog given its src. (Network drive, git-link, etc.)"""
        if not catalog_meta_information:
            catalog_meta_information = CatalogHandler._retrieve_catalog_meta_information(src, branch_name)

        # the path where the catalog lives based on its metadata
        catalog_path = self.album.configuration().get_cache_path_catalog(catalog_meta_information["name"])

        catalog = Catalog(None, catalog_meta_information["name"], catalog_path, src=src, branch_name=branch_name)

        catalog.dispose()

        return catalog

    @staticmethod
    def _create_catalog_cache_if_missing(catalog):
        """Creates the path of a catalog if it is missing."""
        if not catalog.path().exists():
            catalog.path().mkdir(parents=True)

    def _get_divergence_between_catalogs_and_collection(self) -> Dict[str, CatalogUpdates]:
        """Gets the divergence list between all catalogs and the catalog_collection."""
        res = {}
        for catalog in self.get_all():
            res[catalog.name()] = self._get_divergence_between_catalog_and_collection(catalog_name=catalog.name())
        return res

    def _get_divergence_between_catalog_and_collection(self, catalog_name) -> CatalogUpdates:
        """Gets the divergence between a given catalog and the catalog_collection"""
        catalog = self.get_by_name(catalog_name)

        if catalog.is_cache():
            # cache catalog is always up to date since src and path are the same
            return CatalogUpdates(catalog)

        solutions_in_collection = self.album.collection_manager().get_collection_index().get_solutions_by_catalog(
            catalog.catalog_id())
        self.album.migration_manager().load_index(catalog)
        solutions_in_catalog = catalog.index().get_all_solutions()
        solution_changes = self._compare_solutions(solutions_in_collection, solutions_in_catalog)
        return CatalogUpdates(catalog, solution_changes=solution_changes)

    def _update_collection_from_catalogs(self) -> Dict[str, CatalogUpdates]:
        res = {}
        for catalog in self.get_all():
            res[catalog.name()] = self._update_collection_from_catalog(catalog_name=catalog.name())
        return res

    def _update_collection_from_catalog(self, catalog_name) -> CatalogUpdates:
        divergence = self._get_divergence_between_catalog_and_collection(catalog_name)
        # TODO apply changes to catalog attributes
        for change in divergence.solution_changes():
            self.album.collection_manager().solutions().apply_change(divergence.catalog(), change)
        return divergence

    @staticmethod
    def _compare_solutions(solutions_old: List[CollectionIndex.CollectionSolution], solutions_new: List[dict]) -> List[
        SolutionChange]:
        res = []
        # CAUTION: solutions should not be compared based on their id as this might change

        dict_old_coordinates = {}
        list_old_hash = list([s.internal()["hash"] for s in solutions_old])
        for s in solutions_old:
            dict_old_coordinates[dict_to_coordinates(s.setup())] = s

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
            bool(catalog_dict['deletable']),
            catalog_dict['branch_name']
        )
