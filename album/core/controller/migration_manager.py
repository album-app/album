from album.core.model.catalog_index import CatalogIndex

from album.core.concept.singleton import Singleton
from album.core.model.catalog import Catalog
from album.core.model.collection_index import CollectionIndex


class MigrationManager(metaclass=Singleton):

    def __init__(self):
        pass

    def migrate_or_create_collection(self, path, initial_name, initial_version):
        collection = CollectionIndex(initial_name, path)
        self.migrate_catalog_collection(
            collection,
            initial_version,  # current version
            CollectionIndex.version  # target version
        )
        return collection

    def migrate_catalog_collection(self, collection, curr_version, target_version):
        if curr_version == target_version:
            pass
        else:
            # todo: execute catalog_collection migration scripts if necessary!
            # write version to catalog_collection_json!
            raise NotImplementedError(f"Cannot migrate collection from version {curr_version} to version {target_version}.")

    def migrate_catalog_locally(self, curr_version, target_version):
        if curr_version == target_version:
            pass
        else:
            # todo: execute catalog migration scripts if necessary!
            # write version to LOKAL catalog_json! (not remote as it is of c. not possible)
            # update version in the corresponding collection_catalog entry
            raise NotImplementedError(f"Cannot migrate catalog from version {curr_version} to version {target_version}.")

    def convert_catalog(self, catalog: Catalog):
        # read catalog_json to get version
        catalog_meta_information = Catalog.retrieve_catalog_meta_information(catalog.src)
        self.migrate_catalog_locally(catalog_meta_information["version"], CatalogIndex.version)
