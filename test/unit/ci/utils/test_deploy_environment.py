import unittest

from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestDeployEnvironment(TestUnitCoreCommon):

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_get_os_environment_value(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_ci_deploy_values(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_ci_git_config_values(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_ci_project_values(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_ci_zenodo_values(self):
        # todo: implement!
        pass
