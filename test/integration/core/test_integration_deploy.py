import filecmp
import os
import sys
from pathlib import Path
from shutil import copy
from unittest.mock import patch

from album.core.api.model.catalog_updates import ChangeType

from album.core.model.default_values import DefaultValues
from album.core.utils.subcommand import SubProcessError
from album.runner.core.model.coordinates import Coordinates
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationDeploy(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_dry_run(self, conda_lock_mock):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None
        # call
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path()),
            catalog_name=catalog.name(),
            changelog="something changed",
            dry_run=True,
            git_name="MyName",
            git_email="MyEmail",
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertIn("Pretending to deploy", self.captured_output.getvalue())
        self.album_controller.collection_manager().catalogs().update_any("test_catalog")
        updates = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection("test_catalog")
        )
        self.assertIn("test_catalog", updates)
        self.assertEqual(0, len(updates["test_catalog"].solution_changes()))

    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_undeploy_file(self,conda_lock_mock):

        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None
        # call
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("solution11_minimal.py")),
            catalog_name=catalog.name(),
            changelog="something changed",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # deploy a second version
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("solution11_changed_version.py")),
            catalog_name=catalog.name(),
            changelog="something changed",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # deploy a third version
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("solution11_version3.py")),
            catalog_name=catalog.name(),
            changelog="something changed",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # get changes into local collection
        self.album_controller.collection_manager().catalogs().update_any("test_catalog")
        updates = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection("test_catalog")
        )

        # assert if updates contain three solutions
        self.assertIn("test_catalog", updates)
        self.assertEqual(3, len(updates["test_catalog"].solution_changes()))
        # check if first solution was added properly
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            self.album_controller.collection_manager()
            .catalogs()
            .get_by_name("test_catalog")
            .catalog_id(),
            Coordinates("group", "name", "0.1.0"),
        )
        self.assertIsNotNone(solution)
        self.assertIsNotNone(solution.setup()["timestamp"])
        self.assertEqual("something changed", solution.setup()["changelog"])

        # check if current solution file on the catalog is the last one deployed
        remote_solution_file = Path(
            self.album_controller.configuration().get_solution_path_suffix_unversioned(
                Coordinates("group", "name", "0.1.0")
            ),
            DefaultValues.solution_default_name.value,
        )
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            solution_file = Path(tmp_repo.working_tree_dir).joinpath(
                remote_solution_file
            )
            self.assertTrue(solution_file.exists())
            self.assertTrue(
                filecmp.cmp(
                    self.get_test_solution_path("solution11_version3.py"), solution_file
                )
            )

        # undeploy second solution
        self.album_controller.deploy_manager().undeploy(
            "group:name:0.2.0",
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # update collection
        self.album_controller.collection_manager().catalogs().update_any("test_catalog")
        updates = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection("test_catalog")
        )

        # check if the update contains the removal
        self.assertIn("test_catalog", updates)
        self.assertEqual(1, len(updates["test_catalog"].solution_changes()))
        change = updates["test_catalog"].solution_changes()[0]
        self.assertEqual(Coordinates("group", "name", "0.2.0"), change.coordinates())
        self.assertEqual(ChangeType.REMOVED, change.change_type())

        # check if the last version in the repo is still the third one
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            solution_file = Path(tmp_repo.working_tree_dir).joinpath(
                remote_solution_file
            )
            self.assertTrue(solution_file.exists())
            self.assertTrue(
                filecmp.cmp(
                    self.get_test_solution_path("solution11_version3.py"), solution_file
                )
            )

        # undeploy the first third solution
        # this should revert the solution file back to the first version and remove the entry from the database
        self.album_controller.deploy_manager().undeploy(
            "group:name:0.3.0",
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # update collection
        self.album_controller.collection_manager().catalogs().update_any("test_catalog")
        updates = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection("test_catalog")
        )

        # check if the last version in the repo is now the first one
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            solution_file = Path(tmp_repo.working_tree_dir).joinpath(
                remote_solution_file
            )
            self.assertTrue(solution_file.exists())
            self.assertTrue(
                filecmp.cmp(
                    self.get_test_solution_path("solution11_minimal.py"), solution_file
                )
            )

        # undeploy the first version
        self.album_controller.deploy_manager().undeploy(
            "group:name:0.1.0",
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # this should remove the solution files from the repo and remove the entry from the database
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            solution_file = Path(tmp_repo.working_tree_dir).joinpath(
                remote_solution_file
            )
            self.assertFalse(solution_file.exists())

        # update collection
        self.album_controller.collection_manager().catalogs().update_any("test_catalog")
        self.album_controller.collection_manager().catalogs().update_collection(
            "test_catalog"
        )

        # check that all solutions were removed
        solutions = self.album_controller.collection_manager().catalog_collection.get_solutions_by_catalog(
            self.album_controller.collection_manager()
            .catalogs()
            .get_by_name("test_catalog")
            .catalog_id(),
        )
        self.assertEqual(0, len(solutions))

        print(self.captured_output.getvalue())
        self.assertNotIn("WARNING", self.captured_output.getvalue())
        self.assertNotIn("ERROR", self.captured_output.getvalue())

    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_folder_remove_file(self, conda_lock_mock):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None
        coordinates = Coordinates("group", "name", "0.1.0")

        # copy solution and changelog file into new folder
        source = Path(self.tmp_dir.name).joinpath("mysolution")
        source.mkdir(parents=True)
        copy(
            self.get_test_solution_path("solution11_minimal.py"),
            source.joinpath("solution.py"),
        )
        randomfile = source.joinpath("file.md")
        with open(randomfile, "w") as file:
            file.write("my documentation")

        self.album_controller.deploy_manager().deploy(
            str(source),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # check if solution is present and has updated changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates
        )
        self.assertIsNotNone(solution)

        # check if documentation file was deployed into the catalog and copied into the collection cache
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            self.assertTrue(
                Path(tmp_repo.working_tree_dir)
                .joinpath(
                    self.album_controller.configuration().get_solution_path_suffix_unversioned(
                        coordinates
                    ),
                    "file.md",
                )
                .exists()
            )

        # delete a file in the solution dir and deploy again, check if it is gone
        os.remove(randomfile)
        self.album_controller.deploy_manager().deploy(
            str(source),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
            force_deploy=True,
        )
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            self.assertFalse(
                Path(tmp_repo.working_tree_dir)
                .joinpath(
                    self.album_controller.configuration().get_solution_path_suffix_unversioned(
                        coordinates
                    ),
                    "file.md",
                )
                .exists()
            )

    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_file_no_changelog(self, conda_lock_mock):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None

        path = str(self.get_test_solution_path())
        coordinates = Coordinates("group", "name", "0.1.0")

        # run deploy without changelog
        sys.argv = ["", "deploy", path, "test_catalog"]

        # call
        self.album_controller.deploy_manager().deploy(
            path,
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertIn(
            "We recommend documenting changes", self.captured_output.getvalue()
        )

        # check if update exists, solution is present and has updated changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        updates = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection(catalog.name())
        )
        self.assertIn(catalog.name(), updates)
        self.assertEqual(1, len(updates[catalog.name()].solution_changes()))
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates
        )
        self.assertIsNotNone(solution)
        self.assertEqual(None, solution.setup()["changelog"])

    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_file_changelog_parameter(self, conda_lock_mock):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None

        path = str(self.get_test_solution_path())
        coordinates = Coordinates("group", "name", "0.1.0")

        # call with changelog parameter
        self.album_controller.deploy_manager().deploy(
            path,
            catalog_name=catalog.name(),
            dry_run=False,
            changelog="something changed",
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertNotIn(
            "We recommend documenting changes", self.captured_output.getvalue()
        )

        # check if solution has provided changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates
        )
        self.assertIsNotNone(solution)
        self.assertIsNotNone(solution.setup()["timestamp"])
        self.assertEqual("something changed", solution.setup()["changelog"])

    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_folder_changelog_file(self, conda_lock_mock):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None

        coordinates = Coordinates("group", "name", "0.1.0")

        # copy solution and changelog file into new folder
        source = Path(self.tmp_dir.name).joinpath("mysolution")
        source.mkdir(parents=True)
        copy(
            self.get_test_solution_path("solution16_documentation.py"),
            source.joinpath("solution.py"),
        )
        changelog_content = (
            "# Changelog\nAll notable changes to this project will be documented in this file.\n\n"
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), "
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."
            "\n\n## [0.1.0] - %s\n%s\n\n" % ("21/11/25", "- my changes")
        )

        with open(source.joinpath("CHANGELOG.md"), "w") as file:
            file.write(changelog_content)
        with open(source.joinpath("file.md"), "w") as file:
            file.write("my documentation")

        # call providing changelog via file
        self.album_controller.deploy_manager().deploy(
            str(source),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertNotIn(
            "We recommend documenting changes", self.captured_output.getvalue()
        )

        # check if solution is present and has updated changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates
        )
        self.assertIsNotNone(solution)
        self.assertEqual("- my changes", str(solution.setup()["changelog"].strip()))

        # check if documentation file was deployed into the catalog and copied into the collection cache
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_cat_dir")
        ) as tmp_repo:
            self.assertTrue(
                Path(tmp_repo.working_tree_dir)
                .joinpath(
                    self.album_controller.configuration().get_solution_path_suffix_unversioned(
                        coordinates
                    ),
                    "file.md",
                )
                .exists()
            )
    @patch("album.core.controller.resource_manager.create_conda_lock_file")
    def test_deploy_no_conda_lock(self, conda_lock_mock):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        conda_lock_mock.return_value = None
        # call
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path()),
            catalog_name=catalog.name(),
            changelog="something changed",
            dry_run=False,
            git_name="MyName",
            git_email="MyEmail",
            no_conda_lock=True,
        )

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.album_controller.collection_manager().catalogs().update_any("test_catalog")
        updates = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection("test_catalog")
        )
        self.assertIn("test_catalog", updates)
        self.assertEqual(1, len(updates["test_catalog"].solution_changes()))
        conda_lock_mock.assert_not_called()


    def test_deploy_broken_conda_lock(self):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)
        # call and assert
        with self.assertRaises(SubProcessError):
            self.album_controller.deploy_manager().deploy(
                str(self.get_test_solution_path("solution_broken_lock.py")),
                catalog_name=catalog.name(),
                changelog="something changed",
                dry_run=False,
                git_name="MyName",
                git_email="MyEmail",
                no_conda_lock=False,
            )
