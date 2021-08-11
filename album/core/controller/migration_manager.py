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

    def _merge_catalog(self, catalog):
        catalog_entry = self.catalog_collection.get_catalog_by_name(catalog.name)
        catalog_id = catalog_entry["catalog_id"]
        # get changes
        catalog_solution_changes, collection_solution_changes = self.get_changes_solution(catalog)
        catalog_tag_changes, collection_tag_changes = self.get_changes_tag(catalog)
        catalog_solution_tag_changes, collection_solution_tag_changes = self.get_changes_solution_tag(catalog)
        # convert
        # todo: save db file first
        self.convert_solution(catalog_solution_changes, collection_solution_changes, catalog_id)
        self.convert_tag(catalog_tag_changes, collection_tag_changes, catalog_id)
        self.convert_solution_tag(catalog_solution_tag_changes, collection_solution_tag_changes, catalog_id)

    def convert_solution(self, catalog_solution_changes, collection_solution_changes, catalog_id):
        # remove all old solution entries in the collection
        for collection_change in collection_solution_changes:
            self.catalog_collection.remove_solution(
                catalog_id,
                collection_change[0]["group"],
                collection_change[0]["name"],
                collection_change[0]["version"],
            )

        # add all changes
        for catalog_change in catalog_solution_changes:
            self.catalog_collection.insert_solution(
                catalog_id,
                catalog_change[0]
            )

    def convert_tag(self, catalog_tag_changes, collection_tag_changes, catalog_id):
        # remove all old tag entries in the collection
        for collection_change in collection_tag_changes:
            self.catalog_collection.remove_collection_tag(
                catalog_id,
                collection_change[0]["collection_tag_id"],
            )

        # add all changes
        for catalog_change in catalog_tag_changes:
            self.catalog_collection.insert_collection_tag(
                catalog_id,
                catalog_change[0]["tag_id"],
                catalog_change[0]["name"],
                catalog_change[0]["assignment_type"],
                catalog_change[0]["hash"]
            )

    def convert_solution_tag(self, catalog_solution_tag_changes, collection_solution_tag_changes, catalog_id):
        # remove all old tag entries in the collection
        for collection_change in collection_solution_tag_changes:
            self.catalog_collection.remove_collection_solution_tag(
                catalog_id,
                collection_change[0]["collection_solution_tag_id"],
            )

        # add all changes
        for catalog_change in catalog_solution_tag_changes:
            self.catalog_collection.insert_collection_solution_tag(
                catalog_id,
                catalog_change[0]["solution_id"],
                catalog_change[0]["tag_id"],
                catalog_change[0]["hash"]
            )

    def get_changes_solution(self, catalog: Catalog):
        catalog_entry = self.catalog_collection.get_catalog_by_name(catalog.name)
        catalog_id = catalog_entry["catalog_id"]

        collection_solution_entries = self.catalog_collection.get_solutions_by_catalog(catalog_id)
        catalog_solution_entries = catalog.get_all_solutions()

        hash_set_collection_solution = set([entry["hash"] for entry in collection_solution_entries])
        hash_set_catalog_solution = set([entry["hash"] for entry in catalog_solution_entries])

        return self._get_changes_solution(hash_set_collection_solution, hash_set_catalog_solution, catalog)

    def get_changes_tag(self, catalog: Catalog):
        catalog_entry = self.catalog_collection.get_catalog_by_name(catalog.name)
        catalog_id = catalog_entry["catalog_id"]

        collection_tag_entries = self.catalog_collection.get_collection_tags_by_catalog_id(catalog_id)
        catalog_tag_entries = catalog.get_all_tags()

        hash_set_collection_tag = set([entry["hash"] for entry in collection_tag_entries])
        hash_set_catalog_tag = set([entry["hash"] for entry in catalog_tag_entries])

        return self._get_changes_tag(hash_set_collection_tag, hash_set_catalog_tag, catalog)


    def _get_changes_solution_tag(self, set_collection, set_catalog, catalog):
        diff_set = set(set_collection) ^ set(set_catalog)
        collection_catalog_id = self.catalog_collection.get_catalog_by_name(catalog.name)["catalog_id"],
        catalog_changes = []
        collection_changes = []

        for h in diff_set:
            solution_tag = catalog.catalog_index.get_solution_tag_by_hash(h)
            if solution_tag:
                old_collection_solution_tag = \
                    self.catalog_collection.get_collection_solution_tag_by_catalog_id_and_solution_id_and_tag_id(
                        collection_catalog_id,
                        solution_tag["solution_id"],
                        solution_tag["tag_id"]
                    )
                if not old_collection_solution_tag:
                    catalog_changes.append((solution_tag, "add"))
                else:
                    catalog_changes.append((solution_tag, "update"))
            else:
                solution_tag = self.catalog_collection.get_collection_solution_tag_by_catalog_id_and_hash(
                    collection_catalog_id, h
                )

                if not solution_tag:
                    raise RuntimeError("Diff between collection and catalog failed!")

                catalog_solution_tag = catalog.catalog_index.get_solution_tag_by_solution_id_and_tag_id(
                    solution_tag["solution_id"],
                    solution_tag["tag_id"],
                )
                if not catalog_solution_tag:
                    collection_changes.append((solution_tag, "remove"))
                else:
                    collection_changes.append((solution_tag, "modified"))

            return catalog_changes, collection_changes

    def get_changes_solution_tag(self, catalog: Catalog):
        catalog_entry = self.catalog_collection.get_catalog_by_name(catalog.name)
        catalog_id = catalog_entry["catalog_id"]

        collection_solution_tag_entries = self.catalog_collection.get_collection_solution_tags_by_catalog_id(catalog_id)
        catalog_solution_tag_entries = catalog.get_all_solution_tags()

        hash_set_collection_solution_tag = set([entry["hash"] for entry in collection_solution_tag_entries])
        hash_set_catalog_solution_tag = set([entry["hash"] for entry in catalog_solution_tag_entries])

        return self._get_changes_solution_tag(hash_set_collection_solution_tag, hash_set_catalog_solution_tag, catalog)

    def _get_changes_tag(self, set_collection, set_catalog, catalog):
        diff_set = set(set_collection) ^ set(set_catalog)
        collection_catalog_id = self.catalog_collection.get_catalog_by_name(catalog.name)["catalog_id"],
        catalog_changes = []
        collection_changes = []

        for h in diff_set:
            tag = catalog.catalog_index.get_tag_by_hash(h)
            if tag:
                old_collection_tag = self.catalog_collection.get_collection_tag_by_catalog_id_and_name_and_type(
                    collection_catalog_id,
                    tag["name"],
                    tag["assignment_type"]
                )
                if not old_collection_tag:
                    catalog_changes.append((tag, "add"))
                else:
                    catalog_changes.append((tag, "update"))
            else:
                tag = self.catalog_collection.get_collection_tag_by_catalog_id_and_hash(collection_catalog_id, h)

                if not tag:
                    raise RuntimeError("Diff between collection and catalog failed!")

                catalog_tag = catalog.catalog_index.get_tag_by_name_and_type(
                    tag["name"],
                    tag["assignment_type"],
                )
                if not catalog_tag:
                    collection_changes.append((tag, "remove"))
                else:
                    collection_changes.append((tag, "modified"))

            return catalog_changes, collection_changes

    def _get_changes_solution(self, set_collection, set_catalog, catalog):
        diff_set = set(set_collection) ^ set(set_catalog)

        catalog_changes = []
        collection_changes = []
        for h in diff_set:
            # get row
            solution = catalog.catalog_index.get_solution_by_hash(h)
            if solution:
                old_collection_solution = self.catalog_collection.get_solution_by_catalog_grp_name_version(
                    self.catalog_collection.get_catalog_by_name(catalog.name)["catalog_id"],
                    solution["group"],
                    solution["name"],
                    solution["version"]
                )
                if not old_collection_solution:
                    catalog_changes.append((solution, "add"))
                else:
                    catalog_changes.append((solution, "update"))
            else:
                solution = self.catalog_collection.get_solution_by_hash(h)

                if not solution:
                    raise RuntimeError("Diff between collection and catalog failed!")

                catalog_solution = catalog.catalog_index.get_solution_by_group_name_version(
                    solution["group"],
                    solution["name"],
                    solution["version"]
                )
                if not catalog_solution:
                    collection_changes.append((solution, "remove"))
                else:
                    collection_changes.append((solution, "modified"))

        return catalog_changes, collection_changes
