import unittest.suite

import album.core as album
from test.unit.test_unit_common import TestUnitCommon


class TestUnitInit(TestUnitCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        super().setUp()
        # self.something_all_tests_use = some_value

    def tearDown(self) -> None:
        super().tearDown()

    def test_setup(self):
        get_active_solution = album.get_active_solution()
        self.assertIsNone(get_active_solution)
        self.attrs = {
            'name': 'myname',
            'group': 'mygroup',
            'version': 'myversion'
        }
        self.assertIsNone(album.setup_solution(**self.attrs))
        active_solution = album.get_active_solution()
        self.assertIsNotNone(active_solution)
        self.assertEqual("myname", active_solution["name"])
        album.pop_active_solution()


if __name__ == '__main__':
    unittest.main()
