import unittest

from test.unit.test_unit_common import TestUnitCommon


class TestMigrationManager(TestUnitCommon):

    def setUp(self):
        pass

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_migrate_or_create_collection(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_migrate_catalog_collection(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_migrate_catalog_locally(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_convert_catalog(self):
        pass
