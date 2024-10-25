import sys
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from unittest.mock import patch


class TestIntegrationTest(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_test_no_test_routine(self):
        path = self.get_test_solution_path("solution0_dummy_no_routines.py")

        self.fake_install(path, create_environment=True)

        # this solution has the no test() configured
        self.album_controller.test_manager().test(path)

        # assert
        self.assertNotIn("ERROR", self.get_logs_as_string())
        self.assertIn(
            'WARNING No "test" routine configured for solution',
            self.get_logs(),
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    def test_test(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_environment_handler()
            .get_package_manager()
            .get_active_environment_path()
        )

        path = self.get_test_solution_path("solution6_noparent_test.py")

        self.fake_install(path, create_environment=False)

        self.album_controller.test_manager().test(path)

        # assert
        self.assertNotIn("ERROR", self.get_logs_as_string())
        # NOTE: assertion also happens in test routine!

        # todo: change this. first assure subprocess logging is possible in windows
        if sys.platform == "linux" or sys.platform == "darwin":
            log = self.get_logs()
            self.assertIn("solution6_noparent_test_pre_test", log)
            self.assertIn("solution6_noparent_test_run", log)
            self.assertIn("solution6_noparent_test_close", log)
            self.assertIn("solution6_noparent_test_test", log)
