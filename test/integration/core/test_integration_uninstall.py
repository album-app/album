import sys
import unittest
from unittest.mock import patch

from album.argument_parsing import main
from album.core.utils.operations.file_operations import create_path_recursively
from album.runner.model.coordinates import Coordinates
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationUninstall(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_uninstall(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()

        self.assertEqual(
            0,
            len(self.collection_manager.catalog_collection.get_solutions_by_catalog(
                self.collection_manager.catalogs().get_local_catalog().catalog_id()))
        )

        self.fake_install(self.get_test_solution_path(), create_environment=False)

        # lets assume solution had downloads, caches and apps
        p = self.album_instance.configuration().cache_path_tmp_internal().joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_solution_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.album_instance.configuration().cache_path_download().joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_download_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.album_instance.configuration().cache_path_app().joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_app_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        sys.argv = ["", "uninstall", self.get_test_solution_path()]

        self.assertIsNone(main())

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert that solution is removed from the catalog
        self.assertIn("Uninstalled \"name\"", self.captured_output.getvalue())
        solutions = self.collection_manager.get_collection_index().get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id())
        self.assertEqual(1, len(solutions))
        self.assertEqual(0, solutions[0].internal()["installed"])

        # assert that the correct paths are deleted
        self.assertFalse(
            self.album_instance.configuration().cache_path_tmp_internal().joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.album_instance.configuration().cache_path_download().joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.album_instance.configuration().cache_path_app().joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_uninstall_with_routine(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()

        # create test environment
        p = self.get_test_solution_path("solution10_uninstall.py")
        self.fake_install(p, create_environment=False)

        collection = self.collection_manager.catalog_collection
        self.assertTrue(collection.is_installed(
            self.collection_manager.catalogs().get_local_catalog().catalog_id(),
            Coordinates("group", "solution10_uninstall", "0.1.0"))
        )

        # gather arguments
        sys.argv = ["", "uninstall", p]

        # run
        self.assertIsNone(main())

        log = self.captured_output.getvalue()

        self.assertIn("solution10_uninstall_album_uninstall_start", log)
        self.assertIn("solution10_uninstall_album_uninstall_end", log)

        # assert solution was set to uninstalled in the collection
        self.assertEqual(1, len(collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id())))
        self.assertFalse(collection.is_installed(
            self.collection_manager.catalogs().get_local_catalog().catalog_id(),
            Coordinates("group", "solution10_uninstall", "0.1.0"))
        )

    def test_remove_solution_not_installed(self):
        sys.argv = ["", "uninstall", self.get_test_solution_path()]

        with self.assertRaises(SystemExit) as e:
            main()
        self.assertTrue(isinstance(e.exception.code, LookupError))

        self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("Solution not found", e.exception.code.args[0])


if __name__ == '__main__':
    unittest.main()
