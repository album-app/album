import unittest.suite

import hips
from test.unit.test_common import TestHipsCommon


class TestHipsInit(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    def test_setup(self):
        get_active_hips = hips.get_active_hips()
        self.assertIsNone(get_active_hips)
        self.attrs = {
            "name": "myname"
        }
        self.assertIsNone(hips.setup(**self.attrs))
        active_hips = hips.get_active_hips()
        self.assertIsNotNone(active_hips)
        self.assertEqual("myname", active_hips["name"])
        hips.pop_active_hips()


if __name__ == '__main__':
    unittest.main()
