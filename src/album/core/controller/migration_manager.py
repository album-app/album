from album.core.model.catalog import Catalog

from album.core.model.catalog_index import CatalogIndex

from album.core.concept.singleton import Singleton
from album.core.model.collection_index import CollectionIndex


class MigrationManager(metaclass=Singleton):
    """Class handling the migration from Indices of different versions. Responsible for execution of SQL migration!

    Tries to always migrate the catalog index or collection index to the current framework version
    able to deal with the index.

    """

    def __init__(self):
        pass

    def create_collection_index(self, path, initial_name, initial_version) -> CollectionIndex:
        """Creates a Collection Index and migrates its database to the target version."""
        collection_index = CollectionIndex(initial_name, path)
        self.migrate_catalog_collection_db(
            collection_index.path,
            initial_version,  # current version
            CollectionIndex.version  # current framework target version
        )
        return collection_index

    def create_catalog_index(self, path, initial_name, initial_version) -> CatalogIndex:
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
        if catalog.catalog_index is not None:
            catalog.catalog_index.close()
        catalog.catalog_index = self.create_catalog_index(catalog.index_path, catalog.name, CatalogIndex.version)
        catalog.version = catalog.get_version()

    def refresh_index(self, catalog: Catalog) -> bool:
        """Routine to refresh the catalog index. Downloads or copies the index_file."""
        if catalog.update_index_cache_if_possible():
            if catalog.catalog_index:
                catalog.catalog_index.close()
            catalog.catalog_index = self.create_catalog_index(catalog.index_path, catalog.name, CatalogIndex.version)
            return True
        return False
