import sys
import unittest
from io import StringIO

from hips.argument_parsing import main
from hips.core import get_active_hips
from hips.core.model.environment import Environment
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTest(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_test_no_test_routine(self):
        # this solution has the no hips_test() configured
        sys.argv = ["", "test", self.get_test_solution_path("solution0_dummy_no_routines.py")]

        # run
        self.assertIsNone(main())

        # assert
        self.assertIn("WARNING - No \"test\" routine configured for solution", self.captured_output.getvalue())

    def test_test(self):
        # create solution6_noparent_test environment
        Environment({'environment_name': "solution6_noparent_test"}, "unusedCacheName", "unusedCachePath").install()

        # configure silent solution logger
        solution_output = StringIO()
        self.configure_silent_test_logging(solution_output, "solution6_noparent_test", push=False)

        # set up arguments
        sys.argv = ["", "test", self.get_test_solution_path("solution6_noparent_test.py")]

        # run
        self.assertIsNone(main())

        # assert
        # NOTE: assertion also happens in test routine!

        # todo: change this. first assure subprocess logging is possible in windows
        if sys.platform == 'linux' or sys.platform == 'darwin':
            log = solution_output.getvalue()
            self.assertIn("solution6_noparent_test_init", log)
            self.assertIn("solution6_noparent_test_pre_test", log)
            self.assertIn("solution6_noparent_test_run", log)
            self.assertIn("solution6_noparent_test_close", log)
            self.assertIn("solution6_noparent_test_test", log)

        self.assertIsNone(get_active_hips())


if __name__ == '__main__':
    unittest.main()
