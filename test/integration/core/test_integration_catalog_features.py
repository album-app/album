import sys
import unittest
from pathlib import Path

from album.argument_parsing import main
from album.core import Solution
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.model.catalog_updates import ChangeType
from test.integration.test_integration_common import TestIntegrationCommon
from test.unit.test_unit_common import TestUnitCommon


class TestIntegrationCatalogFeatures(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.catalog_configuration = CollectionManager().configuration

    def test_add_remove_catalog(self):
        # prepare
        self.assertIsNotNone(self.catalog_configuration)
        initial_catalogs = self.catalog_configuration.get_initial_catalogs().copy()
        self.assertIsNotNone(initial_catalogs)
        initial_len = len(initial_catalogs)

        # gather arguments add
        new_catalog = Path(self.tmp_dir.name).joinpath("catalog_integration_test")
        CatalogHandler.create_new_catalog(new_catalog, "catalog_integration_test")
        somedir = str(new_catalog)
        sys.argv = ["", "add-catalog", somedir]

        # call
        self.assertIsNone(main())

        # assert
        catalogs = CollectionManager().catalog_collection.get_all_catalogs()
        catalog_cache_path_to_be_deleted = catalogs[-1]["path"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1]["src"])

        # gather arguments remove
        sys.argv = ["", "remove-catalog", somedir]

        # call
        self.assertIsNone(main())

        # assert
        catalogs = CollectionManager().catalog_collection.get_all_catalogs()
        self.assertEqual(initial_len, len(catalogs))
        for catalog in catalogs:
            self.assertIsNotNone(initial_catalogs.get(catalog["name"], None))
        self.assertFalse(Path(catalog_cache_path_to_be_deleted).exists())  # cache path deleted
        self.assertTrue(new_catalog.exists())  # src path still available!

    def test_update_collection(self):
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", "my-catalog")
        CatalogHandler.create_new_catalog(catalog_src, "my-catalog")
        catalog = self.collection_manager.catalogs().add_by_src(catalog_src)
        self.assertTrue(catalog.is_local())
        solution_dict = TestUnitCommon.get_solution_dict()
        solution = Solution(solution_dict)
        solution2_dict = solution_dict.copy()
        solution2_dict["name"] = "something else"
        solution2 = Solution(solution2_dict)

        # check that initially no updates are available

        dif = self.collection_manager.catalogs().update_collection(catalog.name, dry_run=True)

        self.assertIsNotNone(dif)
        self.assertEqual(1, len(dif))
        self.assertIsNotNone(dif[0].catalog_attribute_changes)
        self.assertIsNotNone(dif[0].solution_changes)
        self.assertEqual(0, len(dif[0].catalog_attribute_changes))
        self.assertEqual(0, len(dif[0].solution_changes))

        # add new solution to catalog
        catalog.add(solution)
        catalog.add(solution2)

        dif = self.collection_manager.catalogs().update_collection(catalog.name, dry_run=True)

        self.assertEqual(0, len(dif[0].catalog_attribute_changes))
        self.assertEqual(2, len(dif[0].solution_changes))
        self.assertEqual(ChangeType.ADDED, dif[0].solution_changes[0].change_type)

        # update collection

        dif = self.collection_manager.catalogs().update_collection(catalog.name, dry_run=False)

        self.assertEqual(0, len(dif[0].catalog_attribute_changes))
        self.assertEqual(2, len(dif[0].solution_changes))
        self.assertEqual(ChangeType.ADDED, dif[0].solution_changes[0].change_type)

        dif = self.collection_manager.catalogs().update_collection(catalog.name, dry_run=True)

        self.assertEqual(0, len(dif[0].catalog_attribute_changes))
        self.assertEqual(0, len(dif[0].solution_changes))

        catalog.dispose()

    def test_update_upgrade(self):
        initial_len = len(CollectionManager().catalog_collection.get_all_catalogs())

        # add catalog
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", "my-catalog")
        CatalogHandler.create_new_catalog(catalog_src, "my-catalog")
        catalog = self.collection_manager.catalogs().add_by_src(catalog_src)
        self.assertTrue(catalog.is_local())

        # add new solution to catalog
        solution_dict = TestUnitCommon.get_solution_dict()
        solution = Solution(solution_dict)
        catalog.add(solution)
        catalogs = CollectionManager().catalog_collection.get_all_catalogs()
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(1, len(catalog.catalog_index.get_all_solutions()))

        # update collection
        sys.argv = ["", "update"]
        self.assertIsNone(main())

        # upgrade collection
        sys.argv = ["", "upgrade"]
        self.assertIsNone(main())

        # assert
        solutions = CollectionManager().catalog_collection.get_solutions_by_catalog(catalog.catalog_id)
        print(solutions)
        self.assertEqual(1, len(solutions))

        # compare solution in collection to original solution
        solution_in_collection = solutions[0]
        for key in solution.deploy_keys:
            if key == "timestamp":
                continue
            self.assertEqual(solution[key], solution_in_collection[key])

        catalog.dispose()


if __name__ == '__main__':
    unittest.main()
