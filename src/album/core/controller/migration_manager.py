import json
import pkgutil
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import validate, ValidationError
from packaging import version

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.migration_manager import IMigrationManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.model.catalog_index import CatalogIndex
from album.core.model.collection_index import CollectionIndex
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class MigrationManager(IMigrationManager):
    def __init__(self, album: IAlbumController):
        self.schema_solution = None
        self.schema_solution_runner_0_4_2 = None
        self.album = album

    def migrate_collection_index(
        self, collection_index: ICollectionIndex, initial_version
    ):
        self.migrate_catalog_collection_db(
            collection_index.get_path(),
            initial_version,  # current version
            CollectionIndex.version,  # current framework target version
        )

    def _load_catalog_index(self, catalog: ICatalog, initial_version) -> None:
        """Loads current index on disk and migrates if necessary"""
        catalog.load_index()
        self.migrate_catalog_index_db(
            catalog.index().get_path(),
            initial_version,  # current version
            CatalogIndex.version,  # current framework target version
        )

    def migrate_catalog_collection_db(
        self, collection_index_path, curr_version, target_version
    ):
        if curr_version != target_version:
            # todo: execute catalog_collection SQL migration scripts if necessary!
            # todo: set new version in DB
            raise NotImplementedError(
                'Cannot migrate collection from version "%s" to version "%s"!'
                % (curr_version, target_version)
            )
        return collection_index_path

    def migrate_catalog_index_db(
        self, catalog_index_path, curr_version, target_version
    ):
        if curr_version != target_version:
            # todo: execute catalog index SQL migration scripts if necessary!
            # todo: set new version in DB
            raise NotImplementedError(
                "Cannot migrate collection from version %s to version %s."
                % (curr_version, target_version)
            )
        return catalog_index_path

    def load_index(self, catalog: ICatalog):
        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            catalog.update_index_cache(Path(tmp_dir))
        self._load_catalog_index(catalog, CatalogIndex.version)
        self.album.catalogs().set_version(catalog)

    def refresh_index(self, catalog: ICatalog) -> bool:
        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            if catalog.update_index_cache_if_possible(tmp_dir):
                self._load_catalog_index(catalog, CatalogIndex.version)
                return True
        return False

    def migrate_solution_attrs(self, attrs: dict) -> dict:
        self._load_solution_schema()
        if "album_api_version" not in attrs:
            raise ValidationError(
                "Your setup method is missing the 'album_api_version' keyword - the most recent "
                "version known to this album installation is '0.5.1'."
            )
        api_version = version.parse(attrs["album_api_version"])
        if api_version >= version.parse("0.5.1"):
            validate(attrs, self.schema_solution)
            return attrs
        else:
            validate(attrs, self.schema_solution_runner_0_4_2)
            return self._convert_schema0_schema1(attrs)

    def _load_solution_schema(self):
        if not self.schema_solution:
            data = pkgutil.get_data("album.runner.core.schema", "solution_schema.json")
            self.schema_solution = json.loads(data)
        if not self.schema_solution_runner_0_4_2:
            data = pkgutil.get_data("album.core.schema", "solution_schema_0.4.2.json")
            self.schema_solution_runner_0_4_2 = json.loads(data)

    @staticmethod
    def _convert_schema0_schema1(attrs):
        if "authors" in attrs:
            attrs["solution_creators"] = deepcopy(attrs["authors"])
            attrs.pop("authors")
        return attrs
