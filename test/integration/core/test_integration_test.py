import sys
import unittest

from album.argument_parsing import main
from album.core import get_active_solution
from album.core.model.environment import Environment
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTest(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_test_no_test_routine(self):

        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"))

        # this solution has the no test() configured
        sys.argv = ["", "test", self.get_test_solution_path("solution0_dummy_no_routines.py")]

        # run
        self.assertIsNone(main())

        # assert
        self.assertIn("WARNING - No \"test\" routine configured for solution", self.captured_output.getvalue())

    def test_test_not_installed(self):
        sys.argv = ["", "test", self.get_test_solution_path("solution0_dummy_no_routines.py")]

        # run
        with self.assertRaises(LookupError):
            self.assertIsNone(main())

    def test_test(self):

        # create solution6_noparent_test environment
        env_name = self.collection_manager.catalogs().get_local_catalog().name + "_group_solution6_noparent_test_0.1.0"
        Environment(None, env_name, "unusedCachePath").install()

        self.fake_install(self.get_test_solution_path("solution6_noparent_test.py"))

        # set up arguments
        sys.argv = ["", "test", self.get_test_solution_path("solution6_noparent_test.py")]

        # run
        self.assertIsNone(main())

        # assert
        # NOTE: assertion also happens in test routine!

        # todo: change this. first assure subprocess logging is possible in windows
        if sys.platform == 'linux' or sys.platform == 'darwin':
            log = self.captured_output.getvalue()
            self.assertIn("solution6_noparent_test_pre_test", log)
            self.assertIn("solution6_noparent_test_run", log)
            self.assertIn("solution6_noparent_test_close", log)
            self.assertIn("solution6_noparent_test_test", log)

        self.assertIsNone(get_active_solution())


if __name__ == '__main__':
    unittest.main()
