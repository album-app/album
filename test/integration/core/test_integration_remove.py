import sys
import unittest

from album.argument_parsing import main
from album.core.utils.operations.file_operations import create_path_recursively
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationRemove(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_remove(self):
        self.assertEqual(0, len(self.test_catalog_manager.catalog_collection.get_solutions_by_catalog(self.test_catalog_manager.get_local_catalog().catalog_id)))

        self.fake_install(self.get_test_solution_path(), create_environment=False)

        # lets assume solution had downloads, caches and apps
        p = self.test_catalog_manager.configuration.cache_path_solution.joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_solution_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.test_catalog_manager.configuration.cache_path_download.joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_download_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        p = self.test_catalog_manager.configuration.cache_path_app.joinpath(
            "catalog_local", "group", "name", "0.1.0", "a_cache_app_file.txt"
        )
        create_path_recursively(p.parent)
        p.touch()

        sys.argv = ["", "remove", self.get_test_solution_path()]

        self.assertIsNone(main())

        # assert that solution is removed from the catalog
        self.assertIn("Removed name", self.captured_output.getvalue())
        self.assertEqual(0, len(self.test_catalog_manager.catalog_collection.get_solutions_by_catalog(self.test_catalog_manager.get_local_catalog().catalog_id)))

        # assert that the correct paths are deleted
        self.assertFalse(
            self.test_catalog_manager.configuration.cache_path_solution.joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.test_catalog_manager.configuration.cache_path_download.joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )
        self.assertFalse(
            self.test_catalog_manager.configuration.cache_path_app.joinpath(
                "catalog_local", "group", "name", "0.1.0"
            ).exists()
        )

    def test_remove_solution_not_installed(self):
        sys.argv = ["", "remove", self.get_test_solution_path()]

        with self.assertRaises(LookupError):
            main()


if __name__ == '__main__':
    unittest.main()
