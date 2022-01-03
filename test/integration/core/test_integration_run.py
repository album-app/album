import unittest
from unittest.mock import patch

from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationRun(TestIntegrationCoreCommon):

    def test_run(self):
        # create test environment
        self.fake_install(self.get_test_solution_path())

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(self.get_test_solution_path())
        self.album_instance.run_manager().run(resolve_result)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_arguments(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        p = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(p, create_environment=False)

        # run
        with self.assertRaises(RuntimeError) as e:
            resolve_result = self.album_instance.collection_manager().resolve_and_load(p)
            self.album_instance.run_manager().run(resolve_result)

        # self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("the following arguments are required: --lambda_arg1", e.exception.args[0])

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_arguments_given(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        # create test environment
        p = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(p, create_environment=False)

        # gather arguments
        argv = ["", "--integer_arg1=5",
                    "--integer_arg2=5000",
                    "--string_arg1=MyChosenString",
                    "--lambda_arg1=myFile"]

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(p)
        self.album_instance.run_manager().run(resolve_result, argv=argv)

        self.assertNotIn('ERROR', self.captured_output.getvalue())

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
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        # create test environment
        solution = self.fake_install(self.get_test_solution_path(), create_environment=False)

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            ":".join([solution.coordinates().group(), solution.coordinates().name(), solution.coordinates().version()])
        )
        self.album_instance.run_manager().run(resolve_result)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_minimal_solution(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        self.fake_install(self.get_test_solution_path("solution11_minimal.py"), create_environment=False)

        # this solution has no install() configured

        argv = ["", "run", "", "--log", "DEBUG"]

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            str(self.get_test_solution_path("solution11_minimal.py"))
        )
        self.album_instance.run_manager().run(resolve_result, argv=argv)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn("No \"run\" routine configured for solution", self.captured_output.getvalue())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_parent(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        # fake install what we need
        self.fake_install(self.get_test_solution_path("app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution1_app1.py"), create_environment=False)

        # gather arguments
        argv = ["", "--file", self.closed_tmp_file.name,
                    "--file_solution1_app1", self.closed_tmp_file.name, "--app1_param", "value1"]

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path("solution1_app1.py")
        )
        self.album_instance.run_manager().run(resolve_result, argv=argv)

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert file logs
        with open(self.closed_tmp_file.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(5, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=value1", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("app1_close", log[4])

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_steps(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        # fake install what we need
        self.fake_install(self.get_test_solution_path("app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution3_noparent.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution2_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution1_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution_with_steps.py"), create_environment=False)

        # gather arguments
        argv = ["", "--run-immediately",
                    "--file", self.closed_tmp_file.name, "--file_solution1_app1", self.closed_tmp_file.name]

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path("solution_with_steps.py")
        )
        self.album_instance.run_manager().run(resolve_result, argv=argv)

        self.assertNotIn('ERROR', self.captured_output.getvalue())

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

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_with_grouped_steps(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        self.fake_install(self.get_test_solution_path("app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("app2.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution1_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution2_app1.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution3_noparent.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution4_app2.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution5_app2.py"), create_environment=False)
        self.fake_install(self.get_test_solution_path("solution_with_steps_grouped.py"), create_environment=False)

        # gather arguments
        argv = ["", "--file",
                    self.closed_tmp_file.name, "--file_solution1_app1", self.closed_tmp_file.name]

        # run
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path("solution_with_steps_grouped.py")
        )
        self.album_instance.run_manager().run(resolve_result, argv=argv)

        self.assertNotIn('ERROR', self.captured_output.getvalue())
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


if __name__ == '__main__':
    unittest.main()
