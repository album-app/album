import unittest

from album.core.utils.operations.file_operations import create_path_recursively
from album.runner.core.model.coordinates import Coordinates
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationUninstall(TestIntegrationCoreCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_uninstall(self):

        self.assertEqual(
            0,
            len(self.collection_manager().catalog_collection.get_solutions_by_catalog(
                self.collection_manager().catalogs().get_local_catalog().catalog_id()))
        )

        self.fake_install(self.get_test_solution_path(), create_environment=False)

        resolve_result = self.album_instance.collection_manager().resolve_installed_and_load(self.get_test_solution_path())

        # lets assume solution had downloads, caches and apps
        internal_cache_file = self.album_instance.configuration().lnk_path().joinpath(
            "icache", "0", "a_cache_solution_file.txt"
        )
        create_path_recursively(internal_cache_file.parent)
        internal_cache_file.touch()

        data_file = self.album_instance.configuration().lnk_path().joinpath(
            "data", "0", "a_cache_data_file.txt"
        )
        create_path_recursively(data_file.parent)
        data_file.touch()

        app_file = self.album_instance.configuration().lnk_path().joinpath(
            "pck", "0", "a_cache_app_file.txt"
        )
        create_path_recursively(app_file.parent)
        app_file.touch()

        self.album_instance.install_manager().uninstall(resolve_result)

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # assert that solution is removed from the catalog
        self.assertIn("Uninstalled \"name\"", self.captured_output.getvalue())
        solutions = self.collection_manager().get_collection_index().get_solutions_by_catalog(
            self.collection_manager().catalogs().get_local_catalog().catalog_id())
        self.assertEqual(0, len(solutions))

        # assert that the correct paths are deleted
        self.assertFalse(
            internal_cache_file.parent.exists()
        )
        self.assertFalse(
            data_file.parent.exists()
        )
        self.assertFalse(
            app_file.parent.exists()
        )

    def test_uninstall_with_routine(self):

        # create test environment
        p = self.get_test_solution_path("solution10_uninstall.py")
        self.fake_install(p)

        collection = self.collection_manager().catalog_collection
        self.assertTrue(collection.is_installed(
            self.collection_manager().catalogs().get_local_catalog().catalog_id(),
            Coordinates("group", "solution10_uninstall", "0.1.0"))
        )

        # run
        resolve_result = self.album_instance.collection_manager().resolve_installed_and_load(p)
        self.album_instance.install_manager().uninstall(resolve_result)

        log = self.captured_output.getvalue()

        self.assertIn("solution10_uninstall_album_uninstall_start", log)
        self.assertIn("solution10_uninstall_album_uninstall_end", log)

        # assert solution was set to uninstalled in the collection
        self.assertEqual(0, len(collection.get_solutions_by_catalog(
            self.collection_manager().catalogs().get_local_catalog().catalog_id())))


if __name__ == '__main__':
    unittest.main()
