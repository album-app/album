import unittest.mock

from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestTestManager(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()

    @unittest.skip("Needs to be implemented!")
    def test_test(self):
        # ToDo: implement
        pass


if __name__ == '__main__':
    unittest.main()
