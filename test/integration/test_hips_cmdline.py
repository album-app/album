import os
import sys
import unittest
import unittest.mock
from pathlib import Path

from hips import cmdline


class TestHIPSCommandLine(unittest.TestCase):

    def setUp(self):
        pass

    def test_run(self):
        sys.argv = ["", "run", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())

    def test_run(self):
        sys.argv = ["", "run", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())


def get_dummy_solution_path():
    current_path = Path(os.path.dirname(os.path.realpath(__file__)))
    path = current_path / ".." / "resources" / "dummysolution.py"
    return str(path)


def integration_cmdline_run():
    run_suite = unittest.TestSuite()
    run_suite.addTest(TestHIPSCommandLine('test_run'))
    return run_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    result = runner.run(integration_cmdline_run())

    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)
