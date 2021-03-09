import os
import sys
import unittest.mock
from pathlib import Path

from hips import cmdline


class TestHIPSCommandLine(unittest.TestCase):

    def setUp(self):
        pass

    def test_install(self):
        sys.argv = ["", "install", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())

    # def test_search(self):
    #     sys.argv = ["", "search"]
    #     self.assertIsNone(cmdline.main())

    def test_run(self):
        sys.argv = ["", "run", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())

    # def test_deploy(self):
    #     sys.argv = ["", "deploy", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    def test_tutorial(self):
        sys.argv = ["", "tutorial", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())

    # def test_repl(self):
    #     sys.argv = ["", "repl", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    def test_containerize(self):
        sys.argv = ["", "containerize", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())

    def test_remove(self):
        sys.argv = ["", "remove", get_dummy_solution_path()]
        self.assertIsNone(cmdline.main())


def get_dummy_solution_path():
    current_path = Path(os.path.dirname(os.path.realpath(__file__)))
    path = current_path / ".." / "resources" / "dummysolution.py"
    return str(path)


if __name__ == '__main__':
    if __name__ == '__main__':
        unittest.main()
