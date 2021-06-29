import sys
import tempfile
import unittest.mock
from unittest.mock import patch

import hips.core as hips
from hips.argument_parsing import main
from hips.core.model.environment import Environment
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationRun(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    def test_run(self, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # mock resolving
        res_from_str_mock.side_effect = [{"path": self.get_test_solution_path(), "catalog": "aCatalog"}]

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path()]

        # run
        self.assertIsNone(main())

        # assert
        self.assertIsNone(hips.get_active_hips())

    def test_run_no_run_routine(self):
        # gather arguments
        sys.argv = ["", "run", str(self.get_test_solution_path("solution0_dummy_no_routines.py"))]

        # run
        with self.assertRaises(ValueError) as context:
            main()
            self.assertIn("No \"run\" routine specified for solution", str(context.exception))

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_hips_dependency')
    def test_run_with_parent(self, resolve_mock, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # create app environment
        Environment({'environment_name': "app1"}, "unusedCacheName", "unusedCachePath").install()

        # mock resolving
        resolve_mock.side_effect = self.resolve_hips
        res_from_str_mock.side_effect = [
            {"path": self.get_test_solution_path("solution1_app1.py"), "catalog": "aCatalog"}]

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path("solution1_app1.py"), "--file", self.closed_tmp_file.name,
                    "--file_solution1_app1", self.closed_tmp_file.name, "--app1_param", "value1"]

        # run
        self.assertIsNone(main())

        # assert file logs
        with open(self.closed_tmp_file.name, "r") as f:
            log = f.read().strip().split("\n")
            self.assertEqual(5, len(log))
            self.assertEqual("app1_run", log[0])
            self.assertEqual("app1_param=value1", log[1])
            self.assertEqual("solution1_app1_run", log[2])
            self.assertEqual("solution1_app1_close", log[3])
            self.assertEqual("app1_close", log[4])
            self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_hips_dependency')
    def test_run_with_steps(self, run_resolve_mock, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # create app environment
        Environment({'environment_name': "app1"}, "unusedCacheName", "unusedCachePath").install()

        # create solution3_noparent environment
        Environment({'environment_name': "solution3_noparent"}, "unusedCacheName", "unusedCachePath").install()

        # mock resolving
        run_resolve_mock.side_effect = self.resolve_hips
        res_from_str_mock.side_effect = [
            {"path": self.get_test_solution_path("hips_with_steps.py"), "catalog": "aCatalog"}]

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path("hips_with_steps.py"), "--run-immediately=True", "--file",
                    self.closed_tmp_file.name, "--file_solution1_app1", self.closed_tmp_file.name]

        # run
        self.assertIsNone(main())

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
            self.assertIsNone(hips.get_active_hips())

    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_from_str')
    @patch('hips.core.controller.run_manager.HipsCatalogCollection.resolve_hips_dependency')
    def test_run_with_grouped_steps(self, run_resolve_mock, res_from_str_mock):
        # create test environment
        Environment(None, "unusedCacheName", "unusedCachePath").install()

        # create app environment
        Environment({'environment_name': "app1"}, "unusedCacheName", "unusedCachePath").install()
        Environment({'environment_name': "app2"}, "unusedCacheName", "unusedCachePath").install()

        # create solution3_noparent environment
        Environment({'environment_name': "solution3_noparent"}, "unusedCacheName", "unusedCachePath").install()

        # mock resolving
        run_resolve_mock.side_effect = self.resolve_hips
        res_from_str_mock.side_effect = [
            {"path": self.get_test_solution_path("hips_with_steps_grouped.py"), "catalog": "aCatalog"}
        ]

        # gather arguments
        sys.argv = ["", "run", self.get_test_solution_path("hips_with_steps_grouped.py"), "--file",
                    self.closed_tmp_file.name, "--file_solution1_app1", self.closed_tmp_file.name]

        # run
        self.assertIsNone(main())

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
            self.assertIsNone(hips.get_active_hips())


if __name__ == '__main__':
    unittest.main()
