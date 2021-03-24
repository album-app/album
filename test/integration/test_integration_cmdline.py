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
        sys.argv = ["", "run", get_test_solution_path("solution1_app1.py"), "--file", fp.name, "--file_solution1_app1", fp.name, "--app1_param", "value1"]
        self.assertIsNone(cmdline.main())
        log = open(fp.name, "r").read().strip().split("\n")
        print(log)
        self.assertEqual(5, len(log))
        self.assertEqual("app1_run", log[0])
        self.assertEqual("app1_param=value1", log[1])
        self.assertEqual("solution1_app1_run", log[2])
        self.assertEqual("solution1_app1_close", log[3])
        self.assertEqual("app1_close", log[4])

    @patch('hips.run.resolve_hips')
    @patch('hips.run.set_environment_name')
    def test_run_with_steps(self, run_environment_mock, run_resolve_mock):
        run_resolve_mock.side_effect = self.__resolve_hips
        run_environment_mock.side_effect = self.__set_environment_name
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("hips_with_steps.py"), "--file", fp.name, "--file_solution1_app1", fp.name]
        self.assertIsNone(cmdline.main())
        log = open(fp.name, "r").read().strip().split("\n")
        print(log)
        self.assertEqual(12, len(log))
        self.assertEqual("app1_run", log[0])
        self.assertEqual("app1_param=app1_param_value", log[1])
        self.assertEqual("solution1_app1_run", log[2])
        self.assertEqual("solution1_app1_close", log[3])
        self.assertEqual("app1_close", log[4])
        self.assertEqual("app1_run", log[5])
        self.assertEqual("app1_param=app1_param_other_value", log[6])
        self.assertEqual("solution2_app1_run", log[7])
        self.assertEqual("solution2_app1_close", log[8])
        self.assertEqual("app1_close", log[9])
        self.assertEqual("solution3_noparent_run", log[10])
        self.assertEqual("solution3_noparent_close", log[11])

    @patch('hips.run.resolve_hips')
    @patch('hips.run.set_environment_name')
    def test_run_with_grouped_steps(self, run_environment_mock, run_resolve_mock):
        run_resolve_mock.side_effect = self.__resolve_hips
        run_environment_mock.side_effect = self.__set_environment_name
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        sys.argv = ["", "run", get_test_solution_path("hips_with_steps_grouped.py"), "--file", fp.name, "--file_solution1_app1", fp.name]
        self.assertIsNone(cmdline.main())
        log = open(fp.name, "r").read().strip().split("\n")
        print(log)
        self.assertEqual(16, len(log))
        self.assertEqual("app1_run", log[0])
        self.assertEqual("app1_param=app1_param_value", log[1])
        self.assertEqual("solution1_app1_run", log[2])
        self.assertEqual("solution1_app1_close", log[3])
        self.assertEqual("solution2_app1_run", log[4])
        self.assertEqual("solution2_app1_close", log[5])
        self.assertEqual("app1_close", log[6])
        self.assertEqual("app2_run", log[7])
        self.assertEqual("app2_param=app2_param_value", log[8])
        self.assertEqual("solution4_app2_run", log[9])
        self.assertEqual("solution4_app2_close", log[10])
        self.assertEqual("solution5_app2_run", log[11])
        self.assertEqual("solution5_app2_close", log[12])
        self.assertEqual("app2_close", log[13])
        self.assertEqual("solution3_noparent_run", log[14])
        self.assertEqual("solution3_noparent_close", log[15])

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
