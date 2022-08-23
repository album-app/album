import unittest

from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestContinuousIntegration(TestUnitCoreCommon):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_get_ssh_url(self):
        # todo: implement!
        pass
