import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from album.runner.model.coordinates import Coordinates

from album.argument_parsing import main
from album.core.controller.conda_manager import CondaManager
from album.core.model.default_values import DefaultValues
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationInstall(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    @patch('album.core.controller.conda_manager.CondaManager.install')
    def test_install_minimal_solution(self, install, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()

        # this solution has no install() configured

        sys.argv = ["", "install", str(self.get_test_solution_path("solution11_minimal.py")), "--log", "DEBUG"]

        # run
        self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output)
        self.assertIn("No \"install\" routine configured for solution", self.captured_output.getvalue())

    @patch('album.core.controller.conda_manager.CondaManager.create')
    @patch('album.core.controller.conda_manager.CondaManager.list_environment', return_value=[])
    @patch('album.core.controller.conda_manager.CondaManager.get_environment_dict',
           side_effect=[{}, {"catalog_local_group_name_0.1.0": "aPath"}])
    @patch('album.core.controller.conda_manager.CondaManager.pip_install')
    @patch('album.core.controller.conda_manager.CondaManager.run_scripts')
    def test_install(self, run_scripts_mock, pip_install_mock, get_environment_dict_mock, list_environment_mock,
                     create_mock):
        # gather arguments
        sys.argv = ["", "install", str(self.get_test_solution_path())]

        self.assertIsNone(main())

        # assert solution was added to local catalog
        self.assertNotIn("ERROR", self.captured_output)
        collection = self.collection_manager.catalog_collection
        self.assertEqual(1, len(
            collection.get_solutions_by_catalog(self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(self.collection_manager.catalogs().get_local_catalog().name),
                DefaultValues.cache_path_solution_prefix.value,
                "group", "name", "0.1.0", "solution.py"
            ).exists()
        )

        create_mock.assert_called_once()
        self.assertIsNone(create_mock.call_args[0][0].yaml_file)
        self.assertEqual("catalog_local_group_name_0.1.0", create_mock.call_args[0][0].name)
        list_environment_mock.assert_called_once()
        self.assertEqual(2, get_environment_dict_mock.call_count)
        run_scripts_mock.assert_called_once()
        self.assertEqual("aPath", run_scripts_mock.call_args[0][0].path)
        pip_install_mock.assert_called_once()

    def test_install_twice(self):
        sys.argv = ["", "install", str(self.get_test_solution_path())]
        self.assertIsNone(main())

        self.collection_manager.solutions().is_installed(
            self.collection_manager.catalogs().get_local_catalog(),
            Coordinates("group", "name", "0.1.0")
        )

        sys.argv = ["", "install", str(self.get_test_solution_path())]
        with self.assertRaises(SystemExit) as context:
            main()
            self.assertTrue(isinstance(context.exception.code, RuntimeError))
            self.assertIn("Solution already installed. Uninstall solution first!", context.exception.code.args[0])

    #  @unittest.skipIf(sys.platform == 'win32' or sys.platform == 'cygwin', "This test fails on the Windows CI with \"SSL: CERTIFICATE_VERIFY_FAILED\"")
    @unittest.skip("Fixme")
    def test_install_from_url(self):
        # gather arguments
        sys.argv = ["", "install",
                    "https://gitlab.com/album-app/catalogs/capture-knowledge-dev/-/raw/main/app-fiji/solution.py"]

        self.assertIsNone(main())

        # assert solution was added to local catalog
        self.assertNotIn("ERROR", self.captured_output)
        collection = self.collection_manager.catalog_collection
        self.assertEqual(1, len(
            collection.get_solutions_by_catalog(self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(self.collection_manager.catalogs().get_local_catalog().name),
                DefaultValues.cache_path_solution_prefix.value,
                "ida-mdc", "app-fiji", "0.1.0", "solution.py"
            ).exists()
        )

    def test_install_with_parent(self):
        # gather arguments
        sys.argv = ['', 'install', str(self.get_test_solution_path('app1.py'))]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output)

        sys.argv = ['', 'install', str(self.get_test_solution_path('solution1_app1.py'))]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output)

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(2, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        # assert solution is in the right place and has the right name
        parent_solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(parent_solution_path.exists())
        solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'solution1_app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(solution_path.exists())

    def test_install_with_dependencies(self):
        # fake register app1 dependency but not install
        self.fake_install(str(self.get_test_solution_path("app1.py")), create_environment=False)
        self.collection_manager.solutions().set_uninstalled(
            self.collection_manager.catalogs().get_local_catalog(), Coordinates("group", "app1", "0.1.0")
        )

        # dependency app1 NOT installed
        sys.argv = ["", "install", str(self.get_test_solution_path("solution1_app1.py"))]
        self.assertIsNone(main())

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(2, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        self.assertTrue(self.collection_manager.solutions().is_installed(
            self.collection_manager.catalogs().get_local_catalog(),
            Coordinates("group", "app1", "0.1.0")
        ))

    def test_install_no_solution(self):
        sys.argv = ["", "install"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)


if __name__ == '__main__':
    unittest.main()
