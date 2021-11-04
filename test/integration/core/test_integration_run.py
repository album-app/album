import sys
import unittest
from unittest.mock import patch

from album.core.controller.conda_manager import CondaManager

import album.core as album
from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationRun(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_run(self):
        # create test environment
        self.fake_install(self.get_test_solution_path())

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path()]

        # run
        self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output)
        self.assertIsNone(album.get_active_solution())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_arguments(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        p = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(p, create_environment=False)

        sys.argv = ["", "run", p]  # required arguments not given

        # run
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertTrue(isinstance(e.exception.code, RuntimeError))

        self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("the following arguments are required: --lambda_arg1", e.exception.code.args[0])

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_arguments_given(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        # create test environment
        p = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(p, create_environment=False)

        # gather arguments
        sys.argv = ["", "run", p,
                    "--integer_arg1=5",
                    "--integer_arg2=5000",
                    "--string_arg1=MyChosenString",
                    "--lambda_arg1=myFile"]

        # run
        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output)

        log = self.captured_output.getvalue()

        self.assertIn("integer_arg1", log)
        self.assertIn("5", log)
        self.assertIn("integer_arg2", log)
        self.assertIn("5000", log)
        self.assertIn("string_arg1", log)
        self.assertIn("MyChosenString", log)
        self.assertIn("lambda_arg1", log)
        self.assertIn("MyChosenString", log)
        self.assertIn("myFile.txt", log)
        self.assertIn("None", log)

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_group_name_version(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        # create test environment
        solution = self.fake_install(self.get_test_solution_path(), create_environment=False)

        # gather arguments
        sys.argv = ["", "run", ":".join([solution["group"], solution["name"], solution["version"]])]

        # run
        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output)

        # assert
        self.assertIsNone(album.get_active_solution())

    def test_run_no_run_routine(self):
        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"), create_environment=False)

        # gather arguments
        sys.argv = ["", "run", str(self.get_test_solution_path("solution0_dummy_no_routines.py"))]

        # run
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertTrue(isinstance(e.exception.code, ValueError))

        self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("No \"run\" routine specified for solution", e.exception.code.args[0])

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_parent(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        # fake install what we need
        self.fake_install(self.get_test_solution_path("app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution1_app1.py"), create_environment=False)

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path("solution1_app1.py"), "--file", self.closed_tmp_file.name,
                    "--file_solution1_app1", self.closed_tmp_file.name, "--app1_param", "value1"]

        # run
        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output)

        # assert file logs
        with open(self.closed_tmp_file.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(5, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=value1", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("app1_close", log[4])
            self.assertIsNone(album.get_active_solution())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_steps(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        # fake install what we need
        self.fake_install(self.get_test_solution_path("app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution3_noparent.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution2_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution1_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution_with_steps.py"), create_environment=False)

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path("solution_with_steps.py"),
                    "--run-immediately",
                    "--file", self.closed_tmp_file.name, "--file_solution1_app1", self.closed_tmp_file.name]

        # run
        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output)

        # assert file logs
        with open(self.closed_tmp_file.name, "r") as f:
            log = f.read().strip().split("\n")
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
            self.assertIsNone(album.get_active_solution())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_grouped_steps(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        self.fake_install(self.get_test_solution_path("app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("app2.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution1_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution2_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution3_noparent.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution4_app2.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution5_app2.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution_with_steps_grouped.py"), create_environment=False)

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path("solution_with_steps_grouped.py"), "--file",
                    self.closed_tmp_file.name, "--file_solution1_app1", self.closed_tmp_file.name]

        # run
        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output)
        # assert file logs
        with open(self.closed_tmp_file.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(18, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=app1_param_value", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("solution2_app1_run", log[4])
            self.assertEqual("solution2_app1_close", log[5])
            self.assertEqual("app1_close", log[6])
            self.assertEqual("solution3_noparent_run", log[7])
            self.assertEqual("solution3_noparent_close", log[8])
            self.assertEqual("app2_run", log[9])
            self.assertEqual("app2_param=app2_param_value", log[10])
            self.assertEqual("solution4_app2_run", log[11])
            self.assertEqual("solution4_app2_close", log[12])
            self.assertEqual("solution5_app2_run", log[13])
            self.assertEqual("solution5_app2_close", log[14])
            self.assertEqual("app2_close", log[15])
            self.assertEqual("solution3_noparent_run", log[16])
            self.assertEqual("solution3_noparent_close", log[17])
            self.assertIsNone(album.get_active_solution())


if __name__ == '__main__':
    unittest.main()
