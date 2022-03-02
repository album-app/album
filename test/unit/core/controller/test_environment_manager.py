import unittest.mock

from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestEnvironmentManager(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()
        self.setup_album_controller()
        self.environment_manager = self.album.environment_manager()

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
    def test_remove_environment(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_environment_base_folder(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_run_scripts(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_environment_name(self):
        # ToDo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_disc_content_from_environment(self):
        # ToDo: implement!
        pass