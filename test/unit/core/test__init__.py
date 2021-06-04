import unittest.suite

import hips.core as hips
from test.unit.test_common import TestHipsCommon


class TestHipsInit(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    def tearDown(self) -> None:
        super().tearDown()

    def test_setup(self):
        get_active_hips = hips.get_active_hips()
        self.assertIsNone(get_active_hips)
        self.attrs = {
            "name": "myname",
            "group": "mygroup",
            "version": "myversion"
        }
        self.assertIsNone(hips.setup_hips(**self.attrs))
        active_hips = hips.get_active_hips()
        self.assertIsNotNone(active_hips)
        self.assertEqual("myname", active_hips["name"])
        hips.pop_active_hips()


if __name__ == '__main__':
    unittest.main()
