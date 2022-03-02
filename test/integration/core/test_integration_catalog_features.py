import sys
from pathlib import Path

from album.core.model.default_values import DefaultValues

from album.core.model.catalog_index import CatalogIndex

from album.core.model.catalog_updates import ChangeType
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner.core.model.solution import Solution
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestIntegrationCatalogFeatures(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()
        self.configuration = self.album_controller.configuration()

    def tearDown(self) -> None:
        super().tearDown()

    def add_solutions(self, catalog, solutions):
        with catalog.retrieve_catalog(Path(self.tmp_dir.name).joinpath("tmp_repo")) as tmp_repo:
            tmp_repo.config_writer().set_value("user", "email", "myEmail").release()
            tmp_repo.config_writer().set_value("user", "name", "myName").release()
            catalog.set_index_path(
                Path(tmp_repo.working_tree_dir).joinpath(DefaultValues.catalog_index_file_name.value)
            )
            catalog.load_index()
            for s in solutions:
                len_before = len(catalog.index().get_all_solutions())
                catalog.add(s)
                self.assertEqual(len_before + 1, len(catalog.index().get_all_solutions()))

            tmp_repo.git.add(DefaultValues.catalog_index_file_name.value)
            tmp_repo.git.commit(m="commit_message")
            tmp_repo.git.push()

    def test_add_remove_catalog(self):
        # prepare
        self.assertIsNotNone(self.configuration)
        initial_catalogs = self.configuration.get_initial_catalogs().copy()

        self.assertIsNotNone(initial_catalogs)
        initial_len = 1  # the cache catalog always configured

        new_catalog_src, _ = self.setup_empty_catalog("catalog_integration_test")

        # call
        self.album_controller.collection_manager().catalogs().add_by_src(new_catalog_src)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        catalogs = self.album_controller.collection_manager().get_collection_index().get_all_catalogs()
        catalog_cache_path_to_be_deleted = catalogs[-1]["path"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(str(new_catalog_src), catalogs[len(catalogs) - 1]["src"])

        # gather arguments remove
        sys.argv = ["", "remove-catalog", new_catalog_src]

        # call
        self.album_controller.collection_manager().catalogs().remove_from_collection_by_src(new_catalog_src)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        catalogs = self.album_controller.collection_manager().get_collection_index().get_all_catalogs()
        self.assertEqual(initial_len, len(catalogs))
        for catalog in catalogs:
            if catalog["name"] == "cache_catalog":
                self.assertIsNone(initial_catalogs.get(catalog["name"]))
            else:
                self.assertIsNotNone(initial_catalogs.get(catalog["name"]))
        self.assertFalse(Path(catalog_cache_path_to_be_deleted).exists())  # cache path deleted
        self.assertTrue(new_catalog_src.exists())  # src path still available!

    def test_update_collection(self):
        # create a catalog and its meta file and DB file in a src
        catalog_src, _ = self.setup_empty_catalog("my-catalog")

        # add catalog
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(catalog_src)
        self.assertTrue(catalog.is_local())

        # create two solutions
        solution_dict = TestUnitCoreCommon.get_solution_dict()
        solution = Solution(solution_dict)
        solution2_dict = solution_dict.copy()
        solution2_dict["name"] = "something else"
        solution2 = Solution(solution2_dict)

        # check that initially no updates are available
        dif = self.album_controller.collection_manager().catalogs().update_collection(catalog.name(), dry_run=True)

        self.assertIsNotNone(dif)
        self.assertEqual(1, len(dif.keys()))
        self.assertIsNotNone(dif[catalog.name()])
        self.assertIsNotNone(dif[catalog.name()].catalog_attribute_changes())
        self.assertIsNotNone(dif[catalog.name()].solution_changes())
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(0, len(dif[catalog.name()].solution_changes()))

        # add new solution to catalog
        self.add_solutions(catalog, [solution, solution2])

        dif = self.album_controller.collection_manager().catalogs().update_collection(catalog.name(), dry_run=True)

        self.assertEqual(1, len(dif.keys()))
        self.assertIsNotNone(dif[catalog.name()])
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(2, len(dif[catalog.name()].solution_changes()))
        self.assertEqual(ChangeType.ADDED, dif[catalog.name()].solution_changes()[0].change_type())

        # update collection
        dif = self.album_controller.collection_manager().catalogs().update_collection(catalog.name(), dry_run=False)

        self.assertIsNotNone(dif[catalog.name()])
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(2, len(dif[catalog.name()].solution_changes()))
        self.assertEqual(ChangeType.ADDED, dif[catalog.name()].solution_changes()[0].change_type())

        dif = self.album_controller.collection_manager().catalogs().update_collection(catalog.name(), dry_run=True)

        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(0, len(dif[catalog.name()].solution_changes()))

    def test_update_upgrade(self):
        initial_len = len(
            self.album_controller.collection_manager().get_collection_index().get_all_catalogs())  # has the two default catalogs

        # add catalog
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(catalog_src)  # its emtpy

        # assert it got added
        self.assertEqual(initial_len + 1,
                         len(self.album_controller.collection_manager().get_collection_index().get_all_catalogs()))

        self.assertTrue(catalog.is_local())
        # check its empty
        self.assertEqual(0, len(catalog.index().get_all_solutions()))

        # add new solution to catalog  - not yet in the collection
        solution_dict = TestUnitCoreCommon.get_solution_dict()
        solution_dict["name"] = "myAwesomeSolution"
        solution = Solution(solution_dict)

        self.add_solutions(catalog, [solution])

        # update collection
        sys.argv = ["", "update"]
        dif = self.album_controller.collection_manager().catalogs().update_any()

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # upgrade collection
        sys.argv = ["", "upgrade"]
        dif = self.album_controller.collection_manager().catalogs().update_collection()

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert
        solutions = self.album_controller.collection_manager().get_collection_index().get_solutions_by_catalog(
            catalog.catalog_id())
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
