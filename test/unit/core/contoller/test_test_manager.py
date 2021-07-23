import unittest.mock

from test.unit.test_unit_common import TestUnitCommon


class TestTestManager(TestUnitCommon):

    def setUp(self):
        super().setUp()

    @unittest.skip("Needs to be implemented!")
    def test_test(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__test(self):
        # ToDo: implement
        pass


if __name__ == '__main__':
    unittest.main()
