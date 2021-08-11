import unittest

from album.core.controller.migration_manager import MigrationManager
from test.unit.test_unit_common import TestUnitCommon


class TestMigrationManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_test_config()  # creates migration manager

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_migrate_catalog_collection(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_migrate_catalog_locally(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_convert_catalog(self):
        pass

    # todo: add more tests