import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import get_link_target
from album.runner.core.model.coordinates import Coordinates
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationInstall(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    @patch("album.core.controller.conda_manager.CondaManager.get_environment_path")
    @patch("album.core.controller.conda_manager.CondaManager.install")
    def test_install_minimal_solution(self, _, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )

        # this solution has no install() configured
        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution11_minimal.py")
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # FIXME the next assertion doesn't work since not calling main in this method. Don't know how to set the loglevel to DEBUG in this test.
        # self.assertIn("No \"install\" routine configured for solution", self.captured_output.getvalue())

    def test_install(self):
        self.album_controller.install_manager().install(self.get_test_solution_path())

        # assert solution was added to local catalog
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        collection = self.album_controller.collection_manager().catalog_collection
        self.assertEqual(
            1,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )

        # assert solution is in the right place and has the right name
        self.assertTrue(
            get_link_target(
                Path(self.tmp_dir.name).joinpath(
                    DefaultValues.catalog_folder_prefix.value,
                    str(
                        self.album_controller.collection_manager()
                        .catalogs()
                        .get_cache_catalog()
                        .name()
                    ),
                    DefaultValues.catalog_solutions_prefix.value,
                    "group",
                    "name",
                    "0.1.0",
                )
            )
            .joinpath("solution.py")
            .exists()
        )

    def test_install_from_directory(self):
        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution_in_directory")
        )

        # assert solution was added to local catalog
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        collection = self.album_controller.collection_manager().catalog_collection
        self.assertEqual(
            1,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )

        # assert solution is in the right place and has the right name
        self.assertTrue(
            get_link_target(
                Path(self.tmp_dir.name).joinpath(
                    DefaultValues.catalog_folder_prefix.value,
                    str(
                        self.album_controller.collection_manager()
                        .catalogs()
                        .get_cache_catalog()
                        .name()
                    ),
                    DefaultValues.catalog_solutions_prefix.value,
                    "group",
                    "name",
                    "0.1.0",
                )
            )
            .joinpath("solution.py")
            .exists()
        )

    def test_install_lambda_breaks(self):
        self.assertEqual(
            [],
            self.album_controller.collection_manager().catalog_collection.get_unfinished_installation_solutions(),
        )

        # create test catalog, deploy faulty solution to test catalog
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        self.album_controller.deploy_manager().deploy(
            self.get_test_solution_path("solution13_faulty_routine.py"),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )

        # first, install via path - will add the solution to the local catalog
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(
                self.get_test_solution_path("solution13_faulty_routine.py")
            )

        # call
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(
                self.get_test_solution_path("solution13_faulty_routine.py")
            )

        # the environment stays
        local_catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )
        local_catalog_name = str(local_catalog.name())
        leftover_env_name = local_catalog_name + "_group_faultySolution_0.1.0"
        self.assertTrue(
            self.album_controller.environment_manager()
            .get_package_manager()
            .environment_exists(leftover_env_name)
        )

        # check file is copied
        self.assertTrue(
            self.album_controller.collection_manager()
            .solutions()
            .get_solution_file(
                local_catalog, Coordinates("group", "faultySolution", "0.1.0")
            )
            .exists()
        )

        # try to install faulty solution again
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(
                "group:faultySolution:0.1.0"
            )

        self.assertTrue(
            self.album_controller.collection_manager()
            .solutions()
            .get_solution_file(catalog, Coordinates("group", "faultySolution", "0.1.0"))
            .exists()
        )

        # try to install smth. else (or the same, after routine is fixed)
        # should remove the faulty environment from previously failed installation
        self.album_controller.install_manager().install(self.get_test_solution_path())

        # check cleaned up
        self.assertFalse(
            self.album_controller.environment_manager()
            .get_package_manager()
            .environment_exists(leftover_env_name)
        )
        self.assertEqual(
            [],
            self.album_controller.collection_manager().catalog_collection.get_unfinished_installation_solutions(),
        )

    def test_install_faulty_environment(self):
        self.assertEqual(
            [],
            self.album_controller.collection_manager().catalog_collection.get_unfinished_installation_solutions(),
        )

        # call
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(
                self.get_test_solution_path("solution14_faulty_environment.py")
            )

        # the environment stays
        local_catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )
        local_catalog_name = str(local_catalog.name())
        leftover_env_name = local_catalog_name + "_solution14_faulty_environment_0.1.0"
        self.assertFalse(
            self.album_controller.environment_manager()
            .get_package_manager()
            .environment_exists(leftover_env_name)
        )

        # check file is copied
        local_file = (
            self.album_controller.collection_manager()
            .solutions()
            .get_solution_file(
                local_catalog, Coordinates("group", "faultySolution", "0.1.0")
            )
        )
        self.assertTrue(local_file.exists())

        self.album_controller.install_manager().clean_unfinished_installations()

        self.assertFalse(local_file.exists())
        self.assertEqual(
            [],
            self.album_controller.collection_manager().catalog_collection.get_unfinished_installation_solutions(),
        )

    def test_cleanup_missing_solution_file(self):
        self.assertEqual(
            [],
            self.album_controller.collection_manager().catalog_collection.get_unfinished_installation_solutions(),
        )

        # call
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().install(
                self.get_test_solution_path("solution14_faulty_environment.py")
            )

        local_catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )

        # check file is copied
        local_file = (
            self.album_controller.collection_manager()
            .solutions()
            .get_solution_file(
                local_catalog, Coordinates("group", "faultySolution", "0.1.0")
            )
        )
        self.assertTrue(local_file.exists())
        os.remove(local_file)

        self.album_controller.install_manager().clean_unfinished_installations()

        self.assertFalse(local_file.exists())
        self.assertEqual(
            [],
            self.album_controller.collection_manager().catalog_collection.get_unfinished_installation_solutions(),
        )

    def test_install_twice(self):
        self.album_controller.install_manager().install(self.get_test_solution_path())

        self.album_controller.collection_manager().solutions().is_installed(
            self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            Coordinates("group", "name", "0.1.0"),
        )

        sys.argv = ["", "install", str(self.get_test_solution_path())]
        with self.assertRaises(RuntimeError) as context:
            self.album_controller.install_manager().install(
                self.get_test_solution_path()
            )
            self.assertIn(
                "Solution already installed. Uninstall solution first!",
                context.exception.args[0],
            )

    #  @unittest.skipIf(sys.platform == 'win32' or sys.platform == 'cygwin', "This test fails on the Windows CI with \"SSL: CERTIFICATE_VERIFY_FAILED\"")
    @unittest.skip("Fixme")
    def test_install_from_url(self):
        self.album_controller.install_manager().install(
            "https://gitlab.com/album-app/catalogs/capture-knowledge-dev/-/raw/main/app-fiji/solution.py"
        )

        # assert solution was added to local catalog
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        collection = self.album_controller.collection_manager().catalog_collection
        self.assertEqual(
            1,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id
                )
            ),
        )

        # assert solution is in the right place and has the right name
        self.assertTrue(
            Path(self.tmp_dir.name)
            .joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .name
                ),
                DefaultValues.catalog_solutions_prefix.value,
                "ida-mdc",
                "app-fiji",
                "0.1.0",
                "solution.py",
            )
            .exists()
        )

    def test_install_with_parent(self):
        # install parent app solution
        self.album_controller.install_manager().install(
            self.get_test_solution_path("app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # install child solution
        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # assert both solutions added to local catalog
        collection = self.album_controller.collection_manager().catalog_collection
        self.assertEqual(
            2,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )

        # assert both solution are in the right place and have the right name
        parent_solution_path = get_link_target(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .name()
                ),
                DefaultValues.catalog_solutions_prefix.value,
                "group",
                "app1",
                "0.1.0",
            )
        ).joinpath("solution.py")
        self.assertTrue(parent_solution_path.exists())
        solution_path = get_link_target(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .name()
                ),
                DefaultValues.catalog_solutions_prefix.value,
                "group",
                "solution1_app1",
                "0.1.0",
            )
        ).joinpath("solution.py")
        self.assertTrue(solution_path.exists())

        # uninstall child solution
        self.album_controller.install_manager().uninstall(
            self.get_test_solution_path("solution1_app1.py")
        )

        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # assert that child solution path doesn't exist any more
        solution_path = Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_folder_prefix.value,
            str(
                self.album_controller.collection_manager()
                .catalogs()
                .get_cache_catalog()
                .name()
            ),
            DefaultValues.catalog_solutions_prefix.value,
            "group",
            "solution1_app1",
            "0.1.0",
        )
        self.assertFalse(solution_path.exists())

        # install child solution again
        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution1_app1.py")
        )

        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertTrue(get_link_target(solution_path).exists())

        # uninstall child solution
        self.album_controller.install_manager().uninstall(
            self.get_test_solution_path("solution1_app1.py")
        )

        # uninstall parent solution
        self.album_controller.install_manager().uninstall(
            self.get_test_solution_path("app1.py")
        )

        # install child solution again - this should now fail
        with self.assertRaises(LookupError):
            self.album_controller.install_manager().install(
                self.get_test_solution_path("solution1_app1.py")
            )

    def test_install_with_parent_from_catalog(self):
        # prepare
        tmp_file = Path(self.tmp_dir.name).joinpath("somefile.txt")
        tmp_file.touch()

        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )

        self.album_controller.deploy_manager().deploy(
            self.get_test_solution_path("app1.py"),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )
        self.album_controller.deploy_manager().deploy(
            self.get_test_solution_path("app2.py"),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )

        # install child app solution
        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution1_app1.py")
        )
        self.album_controller.run_manager().run(
            "group:solution1_app1:0.1.0",
            argv=["", "--file_solution1_app1", str(tmp_file)],
        )
        self.album_controller.install_manager().uninstall("group:solution1_app1:0.1.0")

        # do the same thing again, but this time the child solution is in the catalog and addressed via coordinates
        # deploy child solution to catalog
        self.album_controller.deploy_manager().deploy(
            self.get_test_solution_path("solution1_app1.py"),
            catalog_name=catalog.name(),
            dry_run=False,
        )
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )
        # install child solution
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")
        # uninstall child solution
        self.album_controller.install_manager().uninstall("group:solution1_app1:0.1.0")
        # install child solution
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")

        # uninstall child solution
        self.album_controller.install_manager().uninstall("group:solution1_app1:0.1.0")
        # now change the parent of the child solution
        self.album_controller.deploy_manager().deploy(
            self.get_test_solution_path("solution1_app1_changed_parent.py"),
            catalog_name=catalog.name(),
            dry_run=False,
            force_deploy=True,
        )
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )
        # install child solution
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")

    @patch("album.core.controller.conda_manager.CondaManager.get_environment_path")
    @patch("album.core.controller.conda_manager.CondaManager.environment_exists")
    def test_install_with_parent_with_parent(
        self, environment_exists, get_environment_path
    ):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        environment_exists.return_value = True
        # gather arguments
        self.album_controller.install_manager().install(
            self.get_test_solution_path("app1.py")
        )

        self.assertNotIn("ERROR", self.captured_output.getvalue())

        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())

        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution12_solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # assert solution was added to local catalog
        collection = self.album_controller.collection_manager().catalog_collection
        self.assertEqual(
            3,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )

        # assert solution is in the right place and has the right name
        parent_solution_path = get_link_target(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .name()
                ),
                DefaultValues.catalog_solutions_prefix.value,
                "group",
                "app1",
                "0.1.0",
            )
        ).joinpath("solution.py")
        self.assertTrue(parent_solution_path.exists())
        solution_path = get_link_target(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .name()
                ),
                DefaultValues.catalog_solutions_prefix.value,
                "group",
                "solution1_app1",
                "0.1.0",
            )
        ).joinpath("solution.py")
        self.assertTrue(solution_path.exists())
        self.assertTrue(parent_solution_path.exists())
        solution_child_path = get_link_target(
            Path(self.tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                str(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .name()
                ),
                DefaultValues.catalog_solutions_prefix.value,
                "group",
                "solution12_solution1_app1",
                "0.1.0",
            )
        ).joinpath("solution.py")
        self.assertTrue(solution_child_path.exists())

        self.album_controller.install_manager().uninstall(
            self.get_test_solution_path("solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertIn(
            "The following solutions depend on this installation",
            self.captured_output.getvalue(),
        )
        self.assertTrue(solution_path.exists())

        self.album_controller.install_manager().uninstall(
            self.get_test_solution_path("solution12_solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertFalse(solution_child_path.exists())

        self.album_controller.install_manager().uninstall(
            self.get_test_solution_path("solution1_app1.py")
        )

        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertFalse(solution_path.exists())

        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertTrue(solution_path.exists())

        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution12_solution1_app1.py")
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertTrue(solution_child_path.exists())

    def test_install_with_dependencies(self):
        # fake register app1 dependency but not install
        self.fake_install(
            str(self.get_test_solution_path("app1.py")), create_environment=False
        )
        self.album_controller.collection_manager().solutions().set_uninstalled(
            self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            Coordinates("group", "app1", "0.1.0"),
        )

        # dependency app1 NOT installed
        self.album_controller.install_manager().install(
            self.get_test_solution_path("solution1_app1.py")
        )

        # assert solution was added to local catalog
        collection = self.album_controller.collection_manager().catalog_collection
        self.assertEqual(
            2,
            len(
                collection.get_solutions_by_catalog(
                    self.album_controller.collection_manager()
                    .catalogs()
                    .get_cache_catalog()
                    .catalog_id()
                )
            ),
        )

        self.assertTrue(
            self.album_controller.collection_manager()
            .solutions()
            .is_installed(
                self.album_controller.collection_manager()
                .catalogs()
                .get_cache_catalog(),
                Coordinates("group", "app1", "0.1.0"),
            )
        )
