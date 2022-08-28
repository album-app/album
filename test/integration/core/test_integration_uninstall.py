from album.core.utils.operations.file_operations import create_path_recursively
from album.runner.core.model.coordinates import Coordinates
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationUninstall(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_uninstall(self):

        self.assertEqual(
            0,
            len(
                self.album_controller.collection_manager().catalog_collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )

        path = self.get_test_solution_path()

        self.fake_install(path, create_environment=False)

        solution = self.album_controller.collection_manager().resolve_and_load(path)

        # lets assume solution had downloads, caches and apps
        internal_cache_file = (
            solution.loaded_solution()
            .installation()
            .internal_cache_path()
            .joinpath("a_cache_solution_file.txt")
        )
        create_path_recursively(internal_cache_file.parent)
        internal_cache_file.touch()

        data_file = (
            solution.loaded_solution()
            .installation()
            .data_path()
            .joinpath("a_cache_data_file.txt")
        )
        create_path_recursively(data_file.parent)
        data_file.touch()

        app_file = (
            solution.loaded_solution()
            .installation()
            .app_path()
            .joinpath("a_cache_app_file.txt")
        )
        create_path_recursively(app_file.parent)
        app_file.touch()

        self.album_controller.install_manager().uninstall(path)

        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # assert that solution is removed from the catalog
        self.assertIn('Uninstalled "name"', self.captured_output.getvalue())
        solutions = (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solutions_by_catalog(
                self.album_controller.collection_manager()
                .catalogs()
                .get_cache_catalog()
                .catalog_id()
            )
        )
        self.assertEqual(0, len(solutions))

        # assert that the correct paths are deleted
        self.assertFalse(internal_cache_file.parent.exists())
        self.assertFalse(data_file.parent.exists())
        self.assertFalse(app_file.parent.exists())

    def test_uninstall_with_routine(self):

        # create test environment
        p = self.get_test_solution_path("solution10_uninstall.py")
        self.fake_install(p)

        collection = self.album_controller.collection_manager().catalog_collection
        self.assertTrue(
            collection.is_installed(
                self.album_controller.collection_manager()
                .catalogs()
                .get_cache_catalog()
                .catalog_id(),
                Coordinates("group", "solution10_uninstall", "0.1.0"),
            )
        )

        # run
        self.album_controller.install_manager().uninstall(p)

        log = self.captured_output.getvalue()

        self.assertIn("solution10_uninstall_album_uninstall_start", log)
        self.assertIn("solution10_uninstall_album_uninstall_end", log)

        # assert solution was set to uninstalled in the collection
        self.assertEqual(
            0,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )
