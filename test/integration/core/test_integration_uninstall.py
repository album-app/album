from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from unittest.mock import patch

from album.core.utils.operations.file_operations import create_path_recursively
from album.runner.core.model.coordinates import Coordinates


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

        self.assertNotIn("ERROR", self.get_logs_as_string())

        # assert that solution is removed from the catalog
        self.assertIn('Uninstalled "name"', self.get_logs()[-1])
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

        log = self.get_logs_as_string()

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

    def test_uninstall_faulty_solution_with_routine(self):
        # create test environment
        p = self.get_test_solution_path("solution18_uninstall_faulty.py")
        self.fake_install(p)

        collection = self.album_controller.collection_manager().catalog_collection
        self.assertTrue(
            collection.is_installed(
                self.album_controller.collection_manager()
                .catalogs()
                .get_cache_catalog()
                .catalog_id(),
                Coordinates("group", "solution18_uninstall_faulty", "0.1.0"),
            )
        )

        # run
        self.album_controller.install_manager().uninstall(p)

        log = self.get_logs_as_string()

        self.assertIn("Uninstall routine failed! Proceeding anyways", log)

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

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_uninstall_deps_keeps_a_parent_other_solutions_run_in(
        self, _, __, remove_environment
    ):
        install_manager = self.album_controller.install_manager()
        install_manager.install(self.get_test_solution_path("app1.py"))
        install_manager.install(self.get_test_solution_path("solution1_app1.py"))
        install_manager.install(self.get_test_solution_path("solution2_app1.py"))

        # app1 stays, solution2_app1 runs in its environment
        install_manager.uninstall(
            self.get_test_solution_path("solution1_app1.py"), rm_dep=True
        )
        self.assertFalse(self._is_installed("solution1_app1"))
        self.assertTrue(self._is_installed("app1"))
        remove_environment.assert_not_called()

        # with the last solution in its environment, app1 is uninstalled as well
        install_manager.uninstall(
            self.get_test_solution_path("solution2_app1.py"), rm_dep=True
        )
        self.assertFalse(self._is_installed("solution2_app1"))
        self.assertFalse(self._is_installed("app1"))
        remove_environment.assert_called_once()

    def _is_installed(self, name):
        cache_catalog = self.album_controller.catalogs().get_cache_catalog()
        entry = (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                cache_catalog.catalog_id(), Coordinates("group", name, "0.1.0")
            )
        )
        return entry is not None and bool(entry.internal()["installed"])
