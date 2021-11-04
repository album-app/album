import sys
import unittest

from album.argument_parsing import main
from album.core.utils.operations.file_operations import create_path_recursively
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationUninstall(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_uninstall(self):
        self.assertEqual(0, len(self.collection_manager.catalog_collection.get_solutions_by_catalog(self.collection_manager.catalogs().get_local_catalog().catalog_id)))

        self.fake_install(self.get_test_solution_path(), create_environment=False)

        # lets assume solution had downloads, caches and apps
        p = self.collection_manager.configuration.cache_path_solution.joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_solution_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.collection_manager.configuration.cache_path_download.joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_download_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.collection_manager.configuration.cache_path_app.joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_app_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        sys.argv = ["", "uninstall", self.get_test_solution_path()]

        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output)

        # assert that solution is removed from the catalog
        self.assertIn("Uninstalled \"name\"", self.captured_output.getvalue())
        solutions = self.collection_manager.catalog_collection.get_solutions_by_catalog(
            self.collection_manager.catalogs().get_local_catalog().catalog_id)
        self.assertEqual(1, len(solutions))
        self.assertEqual(0, solutions[0]["installed"])

        # assert that the correct paths are deleted
        self.assertFalse(
            self.collection_manager.configuration.cache_path_solution.joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.collection_manager.configuration.cache_path_download.joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.collection_manager.configuration.cache_path_app.joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
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
