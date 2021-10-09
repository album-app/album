import unittest

from album.core.controller.collection.solution_handler import SolutionHandler
from test.unit.core.contoller.collection.test_collection_manager import TestCatalogCollectionCommon


class TestSolutionHandler(TestCatalogCollectionCommon):

    def setUp(self):
        super().setUp()
        self.fill_catalog_collection()
        self.solution_handler = SolutionHandler(self.catalog_collection)

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_path_by_group_name_version(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_path_by_doi(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_add_or_replace(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_solution(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_update_solution(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_keys(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_apply_change(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_installed(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_is_installed(self):
        # todo: implement
        pass
