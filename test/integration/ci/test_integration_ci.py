import sys
import unittest
from pathlib import Path

from album.ci.argument_parsing import main
from album.ci.controller.release_manager import ReleaseManager
from album.core.controller.catalog_manager import CatalogManager
from album.core.controller.deploy_manager import DeployManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy_folder
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCIFeatures(TestIntegrationCommon):

    def setUp(self):
        super().setUp()
        self.src = DefaultValues.catalog_url.value
        self.name = "myTestCatalog"
        self.path = Path(self.tmp_dir.name).joinpath("test_catalog")

    def tearDown(self) -> None:
        super().tearDown()

    def fake_deploy(self):
        self._catalog = Catalog(catalog_id=self.name, path=self.path, src=self.src)

        self._catalog_manager = CatalogManager()
        self._catalog_manager.catalogs.append(self._catalog)

        self._deploy_manager = DeployManager()
        self._deploy_manager.deploy(
            deploy_path=self.get_test_solution_path(),
            catalog=self.name,
            dry_run=True,
            trigger_pipeline=False,
            git_email="myCiUserEmail",
            git_name="myCiUserName",
        )
        copy_folder(self._deploy_manager._repo.working_tree_dir, self.path, copy_root_folder=False)

        self.assertTrue(self.path.is_dir() and self.path.stat().st_size > 0)

        branch_name = "_".join(["group", "name", "0.1.0"])  # solution0_dummy values
        return branch_name

    def test_configure_repo(self):
        # gather arguments
        sys.argv = [
            "",
            "configure-repo",
            self.name,
            str(self.path),
            self.src,
            "--ci_user_name=myCiUserName",
            "--ci_user_email=myCiUserEmail"
        ]

        # run
        self.assertIsNone(main())
        self.assertEqual(
            "myCiUserName", ReleaseManager.instance.catalog_repo.config_reader().get_value("user", "name")
        )
        self.assertEqual(
            "myCiUserEmail", ReleaseManager.instance.catalog_repo.config_reader().get_value("user", "email")
        )

    def test_configure_ssh(self):
        # gather arguments
        sys.argv = [
            "",
            "configure-ssh",
            self.name,
            str(self.path),
            self.src,
            "--ci_project_path=myGitGroup/myTestCatalog"
        ]

        # run
        self.assertIsNone(main())
        self.assertTrue(ReleaseManager.instance.catalog_repo.remote().url.startswith("git@"))
        self.assertIn("myGitGroup/myTestCatalog", ReleaseManager.instance.catalog_repo.remote().url)

    @unittest.skip("Remains untested!")
    def test_zenodo_publish(self):
        pass

    @unittest.skip("Manually activate this if you want a test!")
    def test_zenodo_upload(self):
        # fake deploy to test catalog
        branch_name = self.fake_deploy()

        # gather arguments
        sys.argv = ["", "upload", self.name, str(self.path), self.src, "--branch_name=%s" % branch_name]

        # run
        self.assertIsNone(main())

    def test_update_index(self):
        # fake deploy to test catalog
        branch_name = self.fake_deploy()

        # gather arguments
        sys.argv = ["", "update", self.name, str(self.path), self.src, "--branch_name=%s" % branch_name]

        # run
        self.assertIsNone(main())

    def test_push_changes(self):
        # fake deploy to test catalog
        branch_name = self.fake_deploy()

        # update index
        sys.argv = ["", "update", self.name, str(self.path), self.src, "--branch_name=%s" % branch_name]
        self.assertIsNone(main())

        # gather arguments
        sys.argv = [
            "",
            "push",
            self.name,
            str(self.path),
            self.src,
            "--branch_name=%s" % branch_name,
            "--dry-run=True",
            "--ci_user_name=myCiUserName",
            "--ci_user_email=myCiUserEmail"
        ]

        # run
        self.assertIsNone(main())

        r = ReleaseManager.instance.catalog_repo.index.diff(None)

        self.assertEqual([], r)

    def test_push_changes_no_changes_made(self):
        # fake deploy to test catalog
        branch_name = self.fake_deploy()

        # gather arguments
        sys.argv = [
            "",
            "push",
            self.name,
            str(self.path),
            self.src,
            "--branch_name=%s" % branch_name,
            "--dry-run=True",
            "--ci_user_name=myCiUserName",
            "--ci_user_email=myCiUserEmail"
        ]

        # run
        with self.assertRaises(RuntimeError) as context:
            self.assertIsNone(main())
            self.assertEqual("Diff shows no changes to the repository. Aborting...", str(context.exception))
