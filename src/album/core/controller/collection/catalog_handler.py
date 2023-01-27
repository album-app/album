import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Dict

import validators

from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.controller import IAlbumController
from album.core.api.model.catalog import ICatalog
from album.core.model.catalog import Catalog, retrieve_index_files_from_src
from album.core.model.catalog_index import CatalogIndex
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange, ChangeType
from album.core.model.collection_index import CollectionIndex
from album.core.model.db_version import DBVersion
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.dict_operations import str_to_dict
from album.core.utils.operations.file_operations import (
    force_remove,
    copy,
    get_dict_from_json,
)
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class CatalogHandler(ICatalogHandler):
    """Helper class responsible for catalog handling."""

    def __init__(self, album: IAlbumController):
        self.album = album

    def create_cache_catalog(self):
        name = DefaultValues.cache_catalog_name.value
        local_path = self.album.configuration().get_cache_path_catalog(name)

        # cache catalog always of type direct, deployment not possible anyways
        catalog_meta_information = self.create_new_metadata(local_path, name, "direct")
        catalog = self._create_catalog_from_src(
            local_path, catalog_meta_information, "main", deletable=False
        )
        self._add_to_index(catalog)
        self.album.migration_manager().load_index(catalog)
        self._update_collection_from_catalog(catalog)

    def add_initial_catalogs(self):
        self.create_cache_catalog()
        initial_catalogs = self.album.configuration().get_initial_catalogs()
        initial_catalogs_branch_name = (
            self.album.configuration().get_initial_catalogs_branch_name()
        )
        for catalog in initial_catalogs.keys():
            self.add_by_src(
                str(initial_catalogs[catalog]), initial_catalogs_branch_name[catalog]
            ).dispose()

    def add_by_src(self, source, branch_name="main") -> Catalog:
        # source can be path or url
        source = str(source)
        if not validators.url(source):
            if Path(source).exists():
                source = str(Path(source).resolve())

        catalog_dict = self._get_collection_index().get_catalog_by_src(source)
        if catalog_dict:
            module_logger().warning("Cannot add catalog twice! Doing nothing...")
            return self._as_catalog(catalog_dict)

        catalog_meta_information = self._retrieve_catalog_meta_information(
            source, branch_name
        )
        catalog_dict = self._get_collection_index().get_catalog_by_name(catalog_meta_information["name"])
        if catalog_dict:
            module_logger().warning("Cannot add catalog twice! Doing nothing...")
            return self._as_catalog(catalog_dict)

        catalog = self._create_catalog_from_src(
            source, catalog_meta_information, branch_name
        )

        # always keep the local copy up to date
        if not catalog.is_cache():
            self.album.migration_manager().migrate_catalog_index_db(
                catalog.index_file_path(),  # the path to the catalog
                DBVersion.from_string(catalog_meta_information["version"]),  # eventually outdated remote version
                DBVersion.from_string(DefaultValues.catalog_index_db_version.value)
            )

        self._add_to_index(catalog)
        self._create_catalog_cache_if_missing(catalog)
        self.album.migration_manager().load_index(catalog)

        module_logger().info("Catching catalog content..")
        self._update(catalog)
        self._update_collection_from_catalog(catalog)
        module_logger().info("Added catalog %s!" % source)

        return catalog

    def _add_to_index(self, catalog: ICatalog) -> int:
        catalog_id = self._get_collection_index().insert_catalog(
            catalog.name(),
            str(catalog.src()),
            str(catalog.path()),
            int(catalog.is_deletable()),
            str(catalog.branch_name()),
            str(catalog.type()),
        )
        catalog.set_catalog_id(catalog_id)
        return catalog.catalog_id()

    def get_by_id(self, catalog_id) -> Catalog:
        catalog = self._get_collection_index().get_catalog(catalog_id)
        if not catalog:
            raise LookupError('Catalog with id "%s" not configured!' % catalog_id)
        return self._as_catalog(catalog)

    def _get_collection_index(self):
        return self.album.collection_manager().get_collection_index()

    def get_by_src(self, src) -> Catalog:
        src = str(src)
        catalog_dict = self._get_collection_index().get_catalog_by_src(src)
        if not catalog_dict:
            raise LookupError('Catalog with src "%s" not configured!' % src)
        return self._as_catalog(catalog_dict)

    def get_by_name(self, name) -> Catalog:
        """Looks up a catalog by its id and returns it."""
        name = str(name)
        catalog_dict = self._get_collection_index().get_catalog_by_name(name)
        if not catalog_dict:
            raise LookupError('Catalog with name "%s" not configured!' % name)
        return self._as_catalog(catalog_dict)

    def get_by_path(self, path) -> Catalog:
        path = str(path)
        catalog_dict = self._get_collection_index().get_catalog_by_path(path)
        if not catalog_dict:
            raise LookupError('Catalog with path "%s" not configured!' % path)
        return self._as_catalog(catalog_dict)

    def get_all(self) -> List[Catalog]:
        catalogs = []
        catalog_list = self._get_collection_index().get_all_catalogs()

        for catalog_entry in catalog_list:
            catalogs.append(self._as_catalog(catalog_entry))

        return catalogs

    def get_cache_catalog(self) -> Catalog:
        local_catalog = None
        for catalog in self.get_all():
            if catalog.is_local:
                local_catalog = catalog
                break

        if local_catalog is None:
            raise RuntimeError(
                "Misconfiguration of catalogs. There must be at least one local catalog!"
            )

        return local_catalog

    def create_new_metadata(self, local_path, name, catalog_type):
        local_path = Path(local_path)
        if not local_path.exists():
            local_path.mkdir(parents=True)

        meta_data = (
            '{\"name\": \"'
            + name
            + '\", \"version\": \"'
            + DefaultValues.catalog_index_db_version.value
            + '\", \"type\": \"'
            + catalog_type
            + '\"}'
            )
        with open(local_path.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as meta:
            meta.writelines(meta_data)

        return str_to_dict(meta_data)

    def _update(self, catalog: Catalog) -> bool:
        r = self.album.migration_manager().refresh_index(catalog)
        module_logger().info("Updated catalog %s!" % catalog.name())
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

    def update_collection(
        self, catalog_name=None, dry_run: bool = False, override: bool = False
    ) -> Dict[str, CatalogUpdates]:
        if dry_run:
            if catalog_name:
                catalog = self.get_by_name(catalog_name)
                return {
                    catalog_name: self._get_divergence_between_catalog_and_collection(
                        catalog
                    )
                }
            else:
                return self._get_divergence_between_catalogs_and_collection()
        else:
            if catalog_name:
                catalog = self.get_by_name(catalog_name)
                return {
                    catalog_name: self._update_collection_from_catalog(
                        catalog, override
                    )
                }
            else:
                return self._update_collection_from_catalogs(override)

    def _remove_from_collection(self, catalog_dict) -> Optional[Catalog]:
        try:
            catalog_to_remove = self.get_by_id(catalog_dict["catalog_id"])
        except LookupError as err:
            raise LookupError("Cannot remove catalog! Not configured...") from err

        if not catalog_to_remove.is_deletable():
            raise AttributeError("Cannot remove catalog! Marked as not deletable!")

        installed_solutions = self.get_installed_solutions(catalog_to_remove)

        if installed_solutions:
            installed_solutions_string = ", ".join(
                [str(dict_to_coordinates(i.setup())) for i in installed_solutions]
            )
            raise RuntimeError(
                "Cannot remove catalog! "
                "Has the following solutions installed: %s" % installed_solutions_string
            )

        self._get_collection_index().remove_catalog(catalog_to_remove.catalog_id())

        force_remove(catalog_to_remove.path())

        catalog_to_remove.dispose()

        return catalog_to_remove

    def remove_from_collection_by_path(self, path) -> Optional[Catalog]:
        catalog_dict = self._get_collection_index().get_catalog_by_path(path)

        if not catalog_dict:
            module_logger().warning(
                "Cannot remove catalog, catalog with path %s not found!" % str(path)
            )
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with path %s." % str(path))

        return catalog_to_remove

    def remove_from_collection_by_name(self, name) -> Optional[Catalog]:
        catalog_dict = self._get_collection_index().get_catalog_by_name(name)

        if not catalog_dict:
            module_logger().warning(
                'Cannot remove catalog, catalog with name "%s", not found!' % str(name)
            )
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with name %s." % str(name))

        return catalog_to_remove

    def remove_from_collection_by_src(self, src) -> Optional[Catalog]:
        if not validators.url(str(src)):
            if Path(src).exists():
                src = str(Path(src).resolve())
            else:
                module_logger().warning(
                    'Cannot remove catalog with source "%s"! Not configured!' % str(src)
                )
                return None

        catalog_dict = self._get_collection_index().get_catalog_by_src(src)

        if not catalog_dict:
            module_logger().warning(
                'Cannot remove catalog with source "%s"! Not configured!' % str(src)
            )
            return None

        catalog_to_remove = self._remove_from_collection(catalog_dict)

        module_logger().info("Removed catalog with source %s" % str(src))

        return catalog_to_remove

    def get_installed_solutions(self, catalog: ICatalog):
        installed_solutions = (
            self._get_collection_index().get_all_installed_solutions_by_catalog(
                catalog.catalog_id()
            )
        )
        return installed_solutions

    def get_all_as_dict(self) -> dict:
        return {"catalogs": self._get_collection_index().get_all_catalogs()}

    def set_version(self, catalog: ICatalog):
        # database version
        database_version = catalog.index().get_version()

        # cache version
        meta_dict = get_dict_from_json(catalog.get_meta_file_path())
        meta_version = meta_dict["version"]

        if database_version != meta_version:
            raise ValueError(
                f"Catalog meta information (version {meta_version}) unequal to actual version {database_version}!"
            )

        catalog.set_version(database_version)
        return database_version

    def _retrieve_catalog_meta_information(self, source, branch_name="main"):
        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            repo = Path(tmp_dir).joinpath("repo")
            try:
                _, meta_src = retrieve_index_files_from_src(
                    source, branch_name=branch_name, tmp_dir=repo
                )
                meta_file = copy(
                    meta_src,
                    self.album.configuration()
                    .cache_path_download()
                    .joinpath(DefaultValues.catalog_index_metafile_json.value),
                )
            finally:
                force_remove(repo)

        meta_dict = get_dict_from_json(meta_file)

        return meta_dict

    def _create_catalog_from_src(
        self, src, catalog_meta_information, branch_name="main", deletable=True
    ) -> Catalog:
        """Creates the local cache path for a catalog given its src. (Network drive, git-link, etc.)"""
        # the path where the catalog lives based on its metadata
        catalog_path = self.album.configuration().get_cache_path_catalog(
            catalog_meta_information["name"]
        )

        catalog = Catalog(
            None,
            catalog_meta_information["name"],
            catalog_path,
            src=src,
            branch_name=branch_name,
            catalog_type=catalog_meta_information["type"],
            deletable=deletable,
        )

        catalog.dispose()

        return catalog

    @staticmethod
    def _create_catalog_cache_if_missing(catalog):
        """Creates the path of a catalog if it is missing."""
        if not catalog.path().exists():
            catalog.path().mkdir(parents=True)

    def _get_divergence_between_catalogs_and_collection(
        self,
    ) -> Dict[str, CatalogUpdates]:
        """Gets the divergence list between all catalogs and the catalog_collection."""
        res = {}
        for catalog in self.get_all():
            res[catalog.name()] = self._get_divergence_between_catalog_and_collection(
                catalog=catalog
            )
        return res

    def _get_divergence_between_catalog_and_collection(
        self, catalog: Catalog
    ) -> CatalogUpdates:
        """Gets the divergence between a given catalog and the catalog_collection"""

        if catalog.is_cache():
            # cache catalog is always up to date since src and path are the same
            return CatalogUpdates(catalog)

        solutions_in_collection = self._get_collection_index().get_solutions_by_catalog(
            catalog.catalog_id()
        )
        self.album.migration_manager().load_index(catalog)
        solutions_in_catalog = catalog.index().get_all_solutions()
        solution_changes = self._compare_solutions(
            solutions_in_collection, solutions_in_catalog
        )
        return CatalogUpdates(catalog, solution_changes=solution_changes)

    def _update_collection_from_catalogs(
        self, override: bool = False
    ) -> Dict[str, CatalogUpdates]:
        res = {}
        for catalog in self.get_all():
            res[catalog.name()] = self._update_collection_from_catalog(
                catalog, override
            )
        return res

    def _update_collection_from_catalog(
        self, catalog: Catalog, override: bool = False
    ) -> CatalogUpdates:
        divergence = self._get_divergence_between_catalog_and_collection(catalog)
        # TODO apply changes to catalog attributes
        for change in divergence.solution_changes():
            self.album.solutions().apply_change(divergence.catalog(), change, override)
        return divergence

    @staticmethod
    def _compare_solutions(
        solutions_old: List[CollectionIndex.CollectionSolution],
        solutions_new: List[dict],
    ) -> List[SolutionChange]:
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
                if (
                    coordinates in dict_old_coordinates.keys()
                ):  # changed when metadata in old solution list
                    change = SolutionChange(
                        coordinates,
                        ChangeType.CHANGED,
                        solution_status=dict_old_coordinates[coordinates].internal(),
                    )
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
            catalog_dict["catalog_id"],
            catalog_dict["name"],
            catalog_dict["path"],
            catalog_dict["src"],
            bool(catalog_dict["deletable"]),
            catalog_dict["branch_name"],
            catalog_dict["type"],
        )
