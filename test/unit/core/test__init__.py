import unittest.suite
from pathlib import Path

from album.api.album import Album
from test.unit.test_unit_common import TestUnitCommon


class TestUnitInit(TestUnitCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        super().setUp()
        self.album = Album(base_cache_path=Path(self.tmp_dir.name).joinpath("album"))
        # self.something_all_tests_use = some_value

    def tearDown(self) -> None:
        super().tearDown()

    def test_setup(self):
        get_active_solution = self.album.state_manager().get_active_solution()
        self.assertIsNone(get_active_solution)
        self.attrs = {
            'name': 'myname',
            'group': 'mygroup',
            'version': 'myversion'
        }
        self.assertIsNone(self.album._state_manager._setup_solution(**self.attrs))
        active_solution = self.album.state_manager().get_active_solution()
        self.assertIsNotNone(active_solution)
        self.assertEqual('myname', active_solution.coordinates().name())
        self.album.state_manager().pop_active_solution()


if __name__ == '__main__':
    unittest.main()
