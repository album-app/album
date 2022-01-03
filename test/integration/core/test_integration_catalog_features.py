import sys
import sys
import unittest
from pathlib import Path

from album.argument_parsing import main
from album.core.api.controller.collection.collection_manager import ICollectionManager
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.model.catalog_updates import ChangeType
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner.core.model.solution import Solution
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestIntegrationCatalogFeatures(TestIntegrationCoreCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.catalog_configuration = self.album_instance.configuration()
        self.collection_manager: ICollectionManager = self.album_instance.collection_manager()

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

        # call
        self.collection_manager.catalogs().add_by_src(somedir)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        catalogs = self.collection_manager.get_collection_index().get_all_catalogs()
        catalog_cache_path_to_be_deleted = catalogs[-1]["path"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(somedir, catalogs[len(catalogs) - 1]["src"])

        # gather arguments remove
        sys.argv = ["", "remove-catalog", somedir]

        # call
        self.collection_manager.catalogs().remove_from_collection_by_src(somedir)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        catalogs = self.collection_manager.get_collection_index().get_all_catalogs()
        self.assertEqual(initial_len, len(catalogs))
        for catalog in catalogs:
            self.assertIsNotNone(initial_catalogs.get(catalog["name"], None))
        self.assertFalse(Path(catalog_cache_path_to_be_deleted).exists())  # cache path deleted
        self.assertTrue(new_catalog.exists())  # src path still available!

    def test_update_collection(self):
        # create a catalog and its meta file and DB file in a src
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", "my-catalog")
        CatalogHandler.create_new_catalog(catalog_src, "my-catalog")

        # add catalog
        catalog = self.collection_manager.catalogs().add_by_src(catalog_src)
        self.assertTrue(catalog.is_local())

        # create two solutions
        solution_dict = TestUnitCoreCommon.get_solution_dict()
        solution = Solution(solution_dict)
        solution2_dict = solution_dict.copy()
        solution2_dict["name"] = "something else"
        solution2 = Solution(solution2_dict)

        # check that initially no updates are available
        dif = self.collection_manager.catalogs().update_collection(catalog.name(), dry_run=True)

        self.assertIsNotNone(dif)
        self.assertEqual(1, len(dif.keys()))
        self.assertIsNotNone(dif[catalog.name()])
        self.assertIsNotNone(dif[catalog.name()].catalog_attribute_changes())
        self.assertIsNotNone(dif[catalog.name()].solution_changes())
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(0, len(dif[catalog.name()].solution_changes()))

        # add new solution to catalog
        catalog.add(solution)
        catalog.add(solution2)
        catalog.copy_index_from_cache_to_src()

        dif = self.collection_manager.catalogs().update_collection(catalog.name(), dry_run=True)

        self.assertEqual(1, len(dif.keys()))
        self.assertIsNotNone(dif[catalog.name()])
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(2, len(dif[catalog.name()].solution_changes()))
        self.assertEqual(ChangeType.ADDED, dif[catalog.name()].solution_changes()[0].change_type())

        # update collection

        dif = self.collection_manager.catalogs().update_collection(catalog.name(), dry_run=False)

        self.assertIsNotNone(dif[catalog.name()])
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(2, len(dif[catalog.name()].solution_changes()))
        self.assertEqual(ChangeType.ADDED, dif[catalog.name()].solution_changes()[0].change_type())

        dif = self.collection_manager.catalogs().update_collection(catalog.name(), dry_run=True)

        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(0, len(dif[catalog.name()].solution_changes()))

    def test_update_upgrade(self):
        initial_len = len(self.collection_manager.get_collection_index().get_all_catalogs())  # has the two default catalogs

        # add catalog
        catalog_src = Path(self.tmp_dir.name).joinpath("my-catalogs", "my-catalog")
        CatalogHandler.create_new_catalog(catalog_src, "my-catalog")
        catalog = self.collection_manager.catalogs().add_by_src(catalog_src)  # its emtpy
        # assert it got added
        self.assertEqual(initial_len + 1, len(self.collection_manager.get_collection_index().get_all_catalogs()))

        self.assertTrue(catalog.is_local())
        # check its empty
        self.assertEqual(0, len(catalog.index().get_all_solutions()))

        # add new solution to catalog  - not yet in the collection
        solution_dict = TestUnitCoreCommon.get_solution_dict()
        solution_dict["name"] = "myAwesomeSolution"
        solution = Solution(solution_dict)
        catalog.add(solution)
        # check solution got added
        self.assertEqual(1, len(catalog.index().get_all_solutions()))

        # fake deploy by copying index to src
        catalog.copy_index_from_cache_to_src()

        # update collection
        sys.argv = ["", "update"]
        dif = self.collection_manager.catalogs().update_any()

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # upgrade collection
        sys.argv = ["", "upgrade"]
        dif = self.collection_manager.catalogs().update_collection()

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert
        solutions = self.collection_manager.get_collection_index().get_solutions_by_catalog(catalog.catalog_id())
        self.assertEqual(1, len(solutions))

        # compare solution in collection to original solution
        solution_in_collection = solutions[0]

        sol = {}
        solution_in_col = {}
        for key in get_deploy_dict(solution).keys():
            if key == "timestamp":
                continue
            sol[key] = solution.setup()[key]
            solution_in_col[key] = solution_in_collection.setup()[key]

        self.assertEqual(sol, solution_in_col)

        catalog.dispose()


if __name__ == '__main__':
    unittest.main()
