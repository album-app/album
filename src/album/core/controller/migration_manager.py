import json
import pkgutil

from jsonschema import validate

from album.api.album_interface import AlbumInterface
from album.api.migration_interface import MigrationInterface
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.collection_index import CollectionIndex
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class MigrationManager(MigrationInterface):

    def __init__(self, album: AlbumInterface):
        self.schema_solution = None
        self.collection_manager = album.collection_manager()

    def migrate_collection_index(self, collection_index: CollectionIndex, initial_version):
        self.migrate_catalog_collection_db(
            collection_index.path,
            initial_version,  # current version
            CollectionIndex.version  # current framework target version
        )

    def _create_catalog_index(self, catalog: Catalog, initial_version) -> None:
        catalog.load_index()
        self.migrate_catalog_index_db(
            catalog.catalog_index.path,
            initial_version,  # current version
            CatalogIndex.version  # current framework target version
        )

    def migrate_catalog_collection_db(self, collection_index_path, curr_version, target_version):
        if curr_version != target_version:
            # todo: execute catalog_collection SQL migration scripts if necessary!
            raise NotImplementedError(
                "Cannot migrate collection from version \"%s\" to version \"%s\"!" % (curr_version, target_version)
            )
        return collection_index_path

    def migrate_catalog_index_db(self, catalog_index_path, curr_version, target_version):
        if curr_version != target_version:
            # todo: execute catalog index SQL migration scripts if necessary!
            raise NotImplementedError(
                "Cannot migrate collection from version %s to version %s." % (curr_version, target_version)
            )
        return catalog_index_path

    def load_index(self, catalog: Catalog):
        catalog.update_index_cache()

        self._create_catalog_index(catalog, CatalogIndex.version)
        self.collection_manager.catalogs().set_version(catalog)

    def refresh_index(self, catalog: Catalog) -> bool:
        """Routine to refresh the catalog index. Downloads or copies the index_file."""
        if catalog.update_index_cache_if_possible():
            self._create_catalog_index(catalog, CatalogIndex.version)
            return True
        return False

    def validate_solution_attrs(self, attrs):
        self._load_solution_schema()
        validate(attrs, self.schema_solution)

    def _load_solution_schema(self):
        if not self.schema_solution:
            data = pkgutil.get_data('album.core.schema', 'solution_schema_0.json')
            self.schema_solution = json.loads(data)
