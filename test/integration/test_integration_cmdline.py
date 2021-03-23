import os
import sys
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import patch

from hips import cmdline


class TestHIPSCommandLine(unittest.TestCase):

    def setUp(self):
        pass

    def test_install(self):
        sys.argv = ["", "install", get_test_solution_path()]
        self.assertIsNone(cmdline.main())

    # def test_search(self):
    #     sys.argv = ["", "search"]
    #     self.assertIsNone(cmdline.main())

    def test_run(self):
        sys.argv = ["", "run", get_test_solution_path()]
        self.assertIsNone(cmdline.main())

    @patch('hips.run.resolve_hips')
    @patch('hips.run.set_environment_name')
    def test_run_with_parent(self, environment_name_mock, resolve_mock):
        resolve_mock.side_effect = self.__resolve_hips
        environment_name_mock.side_effect = self.__set_environment_name
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("s2.py"), "--file", fp.name, "--file_s2", fp.name, "--s2_app_param", "value1"]
        self.assertIsNone(cmdline.main())
        log = open(fp.name, "r").read().strip().split("\n")
        print(log)
        self.assertEqual(5, len(log))
        self.assertEqual("s2_app_run", log[0])
        self.assertEqual("s2_app_param=value1", log[1])
        self.assertEqual("s2_run", log[2])
        self.assertEqual("s2_close", log[3])
        self.assertEqual("s2_app_close", log[4])

    @patch('hips.run.resolve_hips')
    @patch('hips.run.set_environment_name')
    def test_run_with_steps(self, run_environment_mock, run_resolve_mock):
        run_resolve_mock.side_effect = self.__resolve_hips
        run_environment_mock.side_effect = self.__set_environment_name
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("s3_steps.py"), "--file", fp.name, "--file_s2", fp.name]
        self.assertIsNone(cmdline.main())
        log = open(fp.name, "r").read().strip().split("\n")
        print(log)
        self.assertEqual(12, len(log))
        self.assertEqual("s2_app_run", log[0])
        self.assertEqual("s2_app_param=s2_app_param_value", log[1])
        self.assertEqual("s2_run", log[2])
        self.assertEqual("s2_close", log[3])
        self.assertEqual("s2_app_close", log[4])
        self.assertEqual("s2_app_run", log[5])
        self.assertEqual("s2_app_param=s2_app_param_other_value", log[6])
        self.assertEqual("s3_run", log[7])
        self.assertEqual("s3_close", log[8])
        self.assertEqual("s2_app_close", log[9])
        self.assertEqual("s3_noparent_run", log[10])
        self.assertEqual("s3_noparent_close", log[11])

    @patch('hips.run.resolve_hips')
    @patch('hips.run.set_environment_name')
    def test_run_with_grouped_steps(self, run_environment_mock, run_resolve_mock):
        run_resolve_mock.side_effect = self.__resolve_hips
        run_environment_mock.side_effect = self.__set_environment_name
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("s3_steps_grouped.py"), "--file", fp.name, "--file_s2", fp.name]
        self.assertIsNone(cmdline.main())
        log = open(fp.name, "r").read().strip().split("\n")
        print(log)
        self.assertEqual(9, len(log))
        self.assertEqual("s2_app_run", log[0])
        self.assertEqual("s2_app_param=s2_app_param_value", log[1])
        self.assertEqual("s2_run", log[2])
        self.assertEqual("s2_close", log[3])
        self.assertEqual("s3_run", log[4])
        self.assertEqual("s3_close", log[5])
        self.assertEqual("s2_app_close", log[6])
        self.assertEqual("s3_noparent_run", log[7])
        self.assertEqual("s3_noparent_close", log[8])

    # def test_deploy(self):
    #     sys.argv = ["", "deploy", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    def test_tutorial(self):
        sys.argv = ["", "tutorial", get_test_solution_path()]
        self.assertIsNone(cmdline.main())

    # def test_repl(self):
    #     sys.argv = ["", "repl", get_dummy_solution_path()]
    #     self.assertIsNone(cmdline.main())

    def test_containerize(self):
        sys.argv = ["", "containerize", get_test_solution_path()]
        self.assertIsNone(cmdline.main())

    def test_remove(self):
        sys.argv = ["", "remove", get_test_solution_path()]
        self.assertIsNone(cmdline.main())

    def __resolve_hips(self, hips_dependency):
        path = get_test_solution_path(hips_dependency['name'] + ".py")
        print(f"resolving path for {hips_dependency} to {path}")
        return path

    def __set_environment_name(self, hips_dependency):
        hips_dependency['_environment_name'] = 'hips'


def get_test_solution_path(solution_file="dummysolution.py"):
    current_path = Path(os.path.dirname(os.path.realpath(__file__)))
    path = current_path / ".." / "resources" / solution_file
    return str(path)


if __name__ == '__main__':
    unittest.main()
