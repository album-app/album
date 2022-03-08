import sys
import unittest
from unittest.mock import patch

from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationTest(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_test_no_test_routine(self):
        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"), create_environment=True)

        # this solution has the no test() configured
        resolve_result = self.album_controller.collection_manager().resolve_and_load(
            self.get_test_solution_path("solution0_dummy_no_routines.py"))
        self.album_controller.test_manager().test(resolve_result)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn("WARNING No \"test\" routine configured for solution", self.captured_output.getvalue())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_test(self, get_environment_path):
        get_environment_path.return_value = self.album_controller.environment_manager().get_conda_manager().get_active_environment_path()

        self.fake_install(self.get_test_solution_path("solution6_noparent_test.py"), create_environment=False)

        resolve_result = self.album_controller.collection_manager().resolve_and_load(
            self.get_test_solution_path("solution6_noparent_test.py"))
        self.album_controller.test_manager().test(resolve_result)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        # NOTE: assertion also happens in test routine!

        # todo: change this. first assure subprocess logging is possible in windows
        if sys.platform == 'linux' or sys.platform == 'darwin':
            log = self.captured_output.getvalue()
            self.assertIn("solution6_noparent_test_pre_test", log)
            self.assertIn("solution6_noparent_test_run", log)
            self.assertIn("solution6_noparent_test_close", log)
            self.assertIn("solution6_noparent_test_test", log)

