import sys
import unittest
from pathlib import Path

from album.ci.argument_parsing import main
from album.ci.controller.release_manager import ReleaseManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy_folder
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCIFeatures(TestIntegrationCommon):

    def setUp(self):
        super().setUp()
        self.src = DefaultValues.default_catalog_src.value
        self.name = "myTestCatalog"
        self.path = Path(self.tmp_dir.name).joinpath("test_catalog")

    def tearDown(self) -> None:
        super().tearDown()

    def fake_deploy(self):
        self._catalog = Catalog(None, name=self.name, path=self.path, src=self.src)

        CollectionManager().catalogs()._add_to_index(self._catalog)

        deploy_manager = DeployManager()
        deploy_manager.deploy(
            deploy_path=self.get_test_solution_path(),
            catalog_name=self.name,
            dry_run=True,
            push_option=None,
            git_email="myCiUserEmail",
            git_name="myCiUserName",
        )
        copy_folder(deploy_manager._repo.working_tree_dir, self.path, copy_root_folder=False)

        self.assertTrue(self.path.is_dir() and self.path.stat().st_size > 0)

        branch_name = "_".join(["group", "name", "0_1_0"])  # solution0_dummy values
        return branch_name

    def test_configure_repo(self):
        # gather arguments
        sys.argv = [
            "",
            "configure-repo",
            self.name,
            str(self.path),
            self.src,
            "--ci-user-name=myCiUserName",
            "--ci-user-email=myCiUserEmail"
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
            "--ci-project-path=myGitGroup/myTestCatalog"
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
        sys.argv = ["", "upload", self.name, str(self.path), self.src, "--branch-name=%s" % branch_name]

        # run
        self.assertIsNone(main())

    def test_update_index(self):
        # fake deploy to test catalog
        branch_name = self.fake_deploy()

        # gather arguments
        sys.argv = ["", "update", self.name, str(self.path), self.src, "--branch-name=%s" % branch_name]

        # run
        self.assertIsNone(main())

    def test_push_changes(self):
        # fake deploy to test catalog
        branch_name = self.fake_deploy()

        # change deployed files so another commit is possible
        with open(self.path.joinpath("catalog", "group", "name", "0_1_0", "name.yml"), "a") as f:
            f.write("\ntest: mytest")

        # gather arguments
        sys.argv = [
            "",
            "push",
            self.name,
            str(self.path),
            self.src,
            "--branch-name=%s" % branch_name,
            "--dry-run",
            "--ci-user-name=myCiUserName",
            "--ci-user-email=myCiUserEmail"
        ]

        # run
        self.assertIsNone(main())

        r = ReleaseManager.instance.catalog_repo.index.diff(None)

        self.assertEqual([], r)
