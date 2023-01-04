from pathlib import Path
from unittest.mock import patch

from album.core.utils.subcommand import SubProcessError
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationRun(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_run(self):
        # create test environment
        self.fake_install(self.get_test_solution_path())

        # run
        self.album_controller.run_manager().run(self.get_test_solution_path())

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_run_arguments(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        p = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(p, create_environment=False)

        # run
        with self.assertRaises(RuntimeError) as e:
            self.album_controller.run_manager().run(p)

        self.assertIn(
            "the following arguments are required: --lambda_arg1",
            self.captured_output.getvalue(),
        )

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_run_arguments_given(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        # create test environment
        p = self.get_test_solution_path("solution8_arguments.py")
        self.fake_install(p, create_environment=False)

        # gather arguments
        argv = [
            "",
            "--integer_arg1=5",
            "--integer_arg2=5000",
            "--file_arg1=aFile",
            "--directory_arg1=aDirectory",
            "--boolean_arg1=True",
            "--string_arg1=MyChosenString",
            "--lambda_arg1=myFile",
        ]

        # run
        self.album_controller.run_manager().run(p, argv=argv)

        log = self.captured_output.getvalue()

        print(log)
        self.assertNotIn("ERROR", log)

        self.assertIn("integer_arg1: <class 'int'> 5", log)
        self.assertIn("integer_arg2: <class 'int'> 5000", log)
        self.assertIn("file_arg1: %s aFile" % str(type(Path())), log)
        self.assertIn("directory_arg1: %s aDirectory" % str(type(Path())), log)
        self.assertIn("boolean_arg1: <class 'bool'> True", log)
        self.assertIn("string_arg1: <class 'str'> MyChosenString", log)
        self.assertIn("lambda_arg1: <class 'str'> myFile.txt", log)
        self.assertIn("lambda_arg2: <class 'NoneType'> None", log)

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_run_with_group_name_version(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        # create test environment
        solution = self.fake_install(
            self.get_test_solution_path(), create_environment=False
        )

        # run
        solution_str = ":".join(
            [
                solution.coordinates().group(),
                solution.coordinates().name(),
                solution.coordinates().version(),
            ]
        )
        self.album_controller.run_manager().run(solution_str)

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_run_minimal_solution(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        self.fake_install(
            self.get_test_solution_path("solution11_minimal.py"),
            create_environment=False,
        )

        # this solution has no install() configured

        argv = ["", "--log", "DEBUG"]

        # run
        self.album_controller.run_manager().run(
            self.get_test_solution_path("solution11_minimal.py"), argv=argv
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertIn(
            'No "run" routine configured for solution', self.captured_output.getvalue()
        )

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_run_with_parent(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        # fake install what we need
        self.fake_install(
            self.get_test_solution_path("app1.py"), create_environment=False
        )
        self.fake_install(
            self.get_test_solution_path("solution1_app1.py"), create_environment=False
        )

        # gather arguments
        argv = [
            "",
            "--file",
            self.closed_tmp_file.name,
            "--file_solution1_app1",
            self.closed_tmp_file.name,
        ]

        # run
        self.album_controller.run_manager().run(
            self.get_test_solution_path("solution1_app1.py"), argv=argv
        )

        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # assert file logs
        with open(self.closed_tmp_file.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(2, len(log))
            self.assertEqual("solution1_app1_run", log[0])
            self.assertEqual("solution1_app1_close", log[1])

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_run_throwing_error_solution(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        path = self.get_test_solution_path(
            "solution15_album_running_faulty_solution.py"
        )
        self.fake_install(path, create_environment=False)

        # run
        with self.assertRaises(SubProcessError) as e:
            self.album_controller.run_manager().run(path)

        print(self.captured_output.getvalue())
        # self.assertIn("INFO ~ print something", self.captured_output.getvalue())
        # self.assertIn("INFO ~ logging info", self.captured_output.getvalue())
        # self.assertEqual(
        #     1, self.captured_output.getvalue().count("INFO ~ logging info")
        # )
        # self.assertIn("WARNING ~ logging warning", self.captured_output.getvalue())
        # self.assertIn("ERROR ~ logging error", self.captured_output.getvalue())
        # self.assertIn(
        #     "INFO ~~~ album in album: print something", self.captured_output.getvalue()
        # )
        # self.assertIn(
        #     "INFO ~~~ album in album: logging info", self.captured_output.getvalue()
        # )
        # self.assertEqual(
        #     1,
        #     self.captured_output.getvalue().count(
        #         "INFO ~~~ album in album: logging info"
        #     ),
        # )
        # self.assertIn(
        #     "WARNING ~~~ album in album: logging warning",
        #     self.captured_output.getvalue(),
        # )
        # self.assertIn(
        #     "ERROR ~~~ album in album: logging error", self.captured_output.getvalue()
        # )
        # self.assertIn(
        #     "INFO ~~~ RuntimeError: Error in run method",
        #     self.captured_output.getvalue(),
        # )

    def test_run_schema0(self):
        path = self.get_test_solution_path("solution17_schema0.py")
        self.album_controller.install_manager().install(path)

        # run
        self.album_controller.run_manager().run(path)
        #print(self.captured_output.getvalue())
        self.assertIn("INFO ~ ['Me']", self.captured_output.getvalue())
