import sys
import unittest
from unittest.mock import patch

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTest(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_test_no_test_routine(self):
        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"), create_environment=True)

        # this solution has the no test() configured
        sys.argv = ["", "test", self.get_test_solution_path("solution0_dummy_no_routines.py")]

        # run
        self.assertIsNone(main())

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn("WARNING - No \"test\" routine configured for solution", self.captured_output.getvalue())

    def test_test_not_installed(self):
        sys.argv = ["", "test", self.get_test_solution_path("solution0_dummy_no_routines.py")]

        # run
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertTrue(isinstance(e.exception.code, LookupError))

        self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("Solution not found", e.exception.code.args[0])

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_test(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().conda_manager.get_active_environment_path()

        self.fake_install(self.get_test_solution_path("solution6_noparent_test.py"), create_environment=False)

        # set up arguments
        sys.argv = ["", "test", self.get_test_solution_path("solution6_noparent_test.py")]

        # run
        self.assertIsNone(main())

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


if __name__ == '__main__':
    unittest.main()
