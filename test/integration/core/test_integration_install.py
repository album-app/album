import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from album.core.model.default_values import DefaultValues
from album.core.utils.subcommand import SubProcessError
from album.runner.core.model.coordinates import Coordinates
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationInstall(TestIntegrationCoreCommon):

    def tearDown(self) -> None:
        super().tearDown()

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    @patch('album.core.controller.conda_manager.CondaManager.install')
    def test_install_minimal_solution(self, _, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()

        # this solution has no install() configured
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path("solution11_minimal.py"))
        self.album_instance.install_manager().install(resolve_result)

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # FIXME the next assertion doesn't work since not calling main in this method. Don't know how to set the loglevel to DEBUG in this test.
        # self.assertIn("No \"install\" routine configured for solution", self.captured_output.getvalue())

    def test_install(self):
        resolve_result = self.album_instance.collection_manager().resolve_and_load(self.get_test_solution_path())
        self.album_instance.install_manager().install(resolve_result)

        # assert solution was added to local catalog
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        collection = self.collection_manager.catalog_collection
        self.assertEqual(1, len(
            collection.get_solutions_by_catalog(self.collection_manager.catalogs().get_local_catalog().catalog_id())))

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(self.collection_manager.catalogs().get_local_catalog().name()),
                DefaultValues.cache_path_solution_prefix.value,
                "group", "name", "0.1.0", "solution.py"
            ).exists()
        )

    def test_install_lambda_breaks(self):

        self.assertEqual([], self.collection_manager.catalog_collection.get_unfinished_installation_solutions())

        # call
        with self.assertRaises(RuntimeError):
            resolve_result = self.album_instance.collection_manager().resolve_and_load(
                self.get_test_solution_path("solution13_faulty_routine.py"))
            self.album_instance.install_manager().install(resolve_result)

        # the environment stays
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        local_catalog_name = str(local_catalog.name())
        leftover_env_name = local_catalog_name + "_group_faultySolution_0.1.0"
        self.assertTrue(self.album_instance.environment_manager().conda_manager.environment_exists(leftover_env_name))

        # check file is copied
        local_file = self.collection_manager.solutions().get_solution_file(local_catalog, Coordinates("group", "faultySolution", "0.1.0"))
        self.assertTrue(local_file.exists())

        # try to install smth. else (or the same, after routine is fixed)
        # should remove the faulty environment from previously failed installation
        resolve_result = self.album_instance.collection_manager().resolve_and_load(self.get_test_solution_path())
        self.album_instance.install_manager().install(resolve_result)

        # check cleaned up
        self.assertFalse(local_file.exists())
        self.assertFalse(self.album_instance.environment_manager().conda_manager.environment_exists(leftover_env_name))
        self.assertEqual([], self.collection_manager.catalog_collection.get_unfinished_installation_solutions())

    def test_install_faulty_environment(self):

        self.assertEqual([], self.collection_manager.catalog_collection.get_unfinished_installation_solutions())

        # call
        with self.assertRaises(RuntimeError):
            resolve_result = self.album_instance.collection_manager().resolve_and_load(
                self.get_test_solution_path("solution14_faulty_environment.py"))
            self.album_instance.install_manager().install(resolve_result)

        # the environment stays
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        local_catalog_name = str(local_catalog.name())
        leftover_env_name = local_catalog_name + "_solution14_faulty_environment_0.1.0"
        self.assertFalse(self.album_instance.environment_manager().conda_manager.environment_exists(leftover_env_name))

        # check file is copied
        local_file = self.collection_manager.solutions().get_solution_file(local_catalog, Coordinates("group", "faultySolution", "0.1.0"))
        self.assertTrue(local_file.exists())

        # try to install smth. else (or the same, after routine is fixed)
        # should remove the faulty environment from previously failed installation
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path())

        self.album_instance.install_manager().install(resolve_result)

        self.assertFalse(local_file.exists())
        self.assertEqual([], self.collection_manager.catalog_collection.get_unfinished_installation_solutions())

    def test_install_twice(self):
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path())
        self.album_instance.install_manager().install(resolve_result)

        self.collection_manager.solutions().is_installed(
            self.collection_manager.catalogs().get_local_catalog(),
            Coordinates("group", "name", "0.1.0")
        )

        sys.argv = ["", "install", str(self.get_test_solution_path())]
        with self.assertRaises(RuntimeError) as context:
            resolve_result = self.album_instance.collection_manager().resolve_and_load(
                self.get_test_solution_path())
            self.album_instance.install_manager().install(resolve_result)
            self.assertIn("Solution already installed. Uninstall solution first!", context.exception.args[0])

    #  @unittest.skipIf(sys.platform == 'win32' or sys.platform == 'cygwin', "This test fails on the Windows CI with \"SSL: CERTIFICATE_VERIFY_FAILED\"")
    @unittest.skip("Fixme")
    def test_install_from_url(self):
        
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            "https://gitlab.com/album-app/catalogs/capture-knowledge-dev/-/raw/main/app-fiji/solution.py")
        self.album_instance.install_manager().install(resolve_result)

        # assert solution was added to local catalog
        self.assertNotIn('ERROR', self.captured_output.getvalue())
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
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('app1.py'))
        self.album_instance.install_manager().install(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(2, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id())))

        # assert solution is in the right place and has the right name
        parent_solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name()),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(parent_solution_path.exists())
        solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name()),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'solution1_app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(solution_path.exists())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().uninstall(resolve_result)

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name()),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'solution1_app1', '0.1.0', 'solution.py'
        )
        self.assertFalse(solution_path.exists())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)

        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertTrue(solution_path.exists())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    @patch('album.core.controller.conda_manager.CondaManager.environment_exists')
    def test_install_with_parent_with_parent(self, environment_exists, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        environment_exists.return_value = True
        # gather arguments
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('app1.py'))
        self.album_instance.install_manager().install(resolve_result)

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution12_solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(3, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id())))

        # assert solution is in the right place and has the right name
        parent_solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name()),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(parent_solution_path.exists())
        solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name()),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'solution1_app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(solution_path.exists())
        self.assertTrue(parent_solution_path.exists())
        solution_child_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(self.collection_manager.catalogs().get_local_catalog().name()),
            DefaultValues.cache_path_solution_prefix.value, 'group',
            'solution12_solution1_app1', '0.1.0', 'solution.py'
        )
        self.assertTrue(solution_child_path.exists())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().uninstall(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn("The following solutions depend on this installation", self.captured_output.getvalue())
        self.assertTrue(solution_path.exists())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution12_solution1_app1.py'))
        self.album_instance.install_manager().uninstall(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertFalse(solution_child_path.exists())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().uninstall(resolve_result)

        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertFalse(solution_path.exists())
        
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertTrue(solution_path.exists())

        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution12_solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertTrue(solution_child_path.exists())

    def test_install_with_dependencies(self):
        # fake register app1 dependency but not install
        self.fake_install(str(self.get_test_solution_path("app1.py")), create_environment=False)
        self.collection_manager.solutions().set_uninstalled(
            self.collection_manager.catalogs().get_local_catalog(), Coordinates("group", "app1", "0.1.0")
        )

        # dependency app1 NOT installed
        resolve_result = self.album_instance.collection_manager().resolve_and_load(
            self.get_test_solution_path('solution1_app1.py'))
        self.album_instance.install_manager().install(resolve_result)

        # assert solution was added to local catalog
        collection = self.collection_manager.catalog_collection
        self.assertEqual(2, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id())))

        self.assertTrue(self.collection_manager.solutions().is_installed(
            self.collection_manager.catalogs().get_local_catalog(),
            Coordinates("group", "app1", "0.1.0")
        ))


if __name__ == '__main__':
    unittest.main()
