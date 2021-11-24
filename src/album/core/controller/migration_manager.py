import json
import pkgutil

from jsonschema import validate

from album.core.concept.singleton import Singleton
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.collection_index import CollectionIndex
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class MigrationManager(metaclass=Singleton):
    """Class handling the migration from Indices of different versions. Responsible for execution of SQL migration!

    Tries to always migrate the catalog index or collection index to the current framework version
    able to deal with the database.

    """

    def __init__(self):
        self.schema_solution = None

    def create_collection_index(self, path, initial_name, initial_version) -> CollectionIndex:
        """Creates a Collection Index and migrates its database to the target version."""
        collection_index = CollectionIndex(initial_name, path)
        self.migrate_catalog_collection_db(
            collection_index.path,
            initial_version,  # current version
            CollectionIndex.version  # current framework target version
        )
        return collection_index

    def _create_catalog_index(self, path, initial_name, initial_version) -> CatalogIndex:
        catalog_index = CatalogIndex(initial_name, path)
        self.migrate_catalog_index_db(
            catalog_index.path,
            initial_version,  # current version
            CatalogIndex.version  # current framework target version
        )
        return catalog_index

    def migrate_catalog_collection_db(self, collection_index_path, curr_version, target_version):
        """Migrates a given collection index to the target version."""
        if curr_version != target_version:
            # todo: execute catalog_collection SQL migration scripts if necessary!
            raise NotImplementedError(
                "Cannot migrate collection from version \"%s\" to version \"%s\"!" % (curr_version, target_version)
            )
        return collection_index_path

    def migrate_catalog_index_db(self, catalog_index_path, curr_version, target_version):
        """Migrates the index of a given catalog to the current framework version if possible."""
        if curr_version != target_version:
            # todo: execute catalog index SQL migration scripts if necessary!
            raise NotImplementedError(
                "Cannot migrate collection from version %s to version %s." % (curr_version, target_version)
            )
        return catalog_index_path

    def load_index(self, catalog: Catalog):
        """Loads the index from file or src. If a file and src exists routine tries to update the index."""
        catalog.update_index_cache()

        catalog.catalog_index = self._create_catalog_index(catalog.index_path, catalog.name, CatalogIndex.version)
        catalog.version = catalog.get_version()

    def refresh_index(self, catalog: Catalog) -> bool:
        """Routine to refresh the catalog index. Downloads or copies the index_file."""
        if catalog.update_index_cache_if_possible():
            catalog.catalog_index = self._create_catalog_index(catalog.index_path, catalog.name, CatalogIndex.version)

            return True
        return False

    def validate_solution_attrs(self, attrs):
        self.load_solution_schema()
        validate(attrs, self.schema_solution)

    def load_solution_schema(self):
        if not self.schema_solution:
            data = pkgutil.get_data('album.core.schema', 'solution_schema_0.json')
            self.schema_solution = json.loads(data)
