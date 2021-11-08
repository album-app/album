import unittest.mock

from album.core.controller.environment_manager import EnvironmentManager
from test.unit.test_unit_common import TestUnitCommon


class TestEnvironmentManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.environment_manager = EnvironmentManager()

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_install_environment(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_environment(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_environment_name(self):
        # ToDo: implement!
        pass
