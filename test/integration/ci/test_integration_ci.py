import sys
import unittest
from pathlib import Path

import git

from album.ci.argument_parsing import main
from album.core.model.catalog import Catalog
from album.core.utils.operations.git_operations import checkout_branch
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationCIFeatures(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()
        self.name = "test_catalog"
        self.src, _ = self.setup_empty_catalog(self.name, catalog_type="request")
        self.path = Path(self.tmp_dir.name).joinpath("test_catalog_repo_clone")
        self.repo = None

    def tearDown(self) -> None:
        super().tearDown()

    def deploy_request(self):
        catalog_cache_path = Path(self.tmp_dir.name).joinpath("test_catalog_cache")
        self._catalog = Catalog(None, name=self.name, path=catalog_cache_path, src=self.src, catalog_type="request")

        self.album_controller.catalogs()._add_to_index(self._catalog)

        self.album_controller.deploy_manager().deploy(
            deploy_path=self.get_test_solution_path(),
            catalog_name=self.name,
            dry_run=False,
            push_options=None,
            git_email="myCiUserEmail",
            git_name="myCiUserName",
        )

        # get the catalog repo
        with self._catalog.retrieve_catalog(self.path) as repo:
            self.repo = repo

        branch_name = "_".join(["group", "name", "0.1.0"])  # solution0_dummy values
        return branch_name

    def test_configure_repo(self):
        # gather arguments
        sys.argv = [
            "",
            "configure-repo",  # command
            self.name,  # catalog_name
            str(self.path),  # catalog_repo_clone_path
            str(self.src),  # catalog_src
            "--ci-user-name=myCiUserName",
            "--ci-user-email=myCiUserEmail"
        ]

        # run
        self.assertIsNone(main())
        self.assertEqual(
            "myCiUserName", git.Repo(self.path).config_reader().get_value("user", "name")
        )
        self.assertEqual(
            "myCiUserEmail", git.Repo(self.path).config_reader().get_value("user", "email")
        )

    def test_configure_ssh(self):
        # gather arguments
        sys.argv = [
            "",
            "configure-ssh",
            self.name,
            str(self.path),
            str(self.src),
            "--ci-project-path=myGitGroup/myTestCatalog"
        ]

        # run
        self.assertIsNone(main())
        self.assertTrue(git.Repo(self.path).remote().url.startswith("git@"))
        self.assertIn("myGitGroup/myTestCatalog", git.Repo(self.path).remote().url)

    @unittest.skip("Remains untested!")
    def test_zenodo_publish(self):
        pass

    @unittest.skip("Manually activate this if you want a test!")
    def test_zenodo_upload(self):
        # deploy request to test catalog
        branch_name = self.deploy_request()

        # gather arguments
        sys.argv = ["", "upload", self.name, str(self.path), self.src, "--branch-name=%s" % branch_name]

        # run
        self.assertIsNone(main())

    def test_update_index(self):
        # deploy request to test catalog
        branch_name = self.deploy_request()

        # gather arguments
        sys.argv = ["", "update", self.name, str(self.path), str(self.src), "--branch-name=%s" % branch_name]

        # run
        self.assertIsNone(main())

        r_repo = git.Repo(self.path)

        # assert
        self.assertEqual(r_repo.active_branch.name, "group_name_0.1.0")
        self.assertListEqual(["album_catalog_index.db", "album_solution_list.json"], r_repo.untracked_files)

    def test_commit_changes(self):
        # deploy request to test catalog
        branch_name = self.deploy_request()

        # checkout this branch
        head = checkout_branch(self.repo, branch_name)

        # save commit message
        self.assertEqual("Adding new/updated group_name_0.1.0\n", head.commit.message)

        # change deployed files so another commit is possible
        with open(self.path.joinpath("solutions", "group", "name", "name.yml"), "a") as f:
            f.write("\ntest: mytest")

        # gather arguments
        sys.argv = [
            "",
            "commit",
            self.name,
            str(self.path),
            str(self.src),
            "--branch-name=%s" % branch_name,
            "--ci-user-name=myCiUserName",
            "--ci-user-email=myCiUserEmail"
        ]

        # run
        self.assertIsNone(main())

        r_repo = git.Repo(self.path)

        # check out last commit
        self.assertEqual(r_repo.active_branch.name, "group_name_0.1.0")
        self.assertEqual("Prepared branch \"group_name_0.1.0\" for merging.\n", r_repo.active_branch.commit.message)

    @unittest.skip("Needs to be implemented!")
    def test_merge(self):
        # todo: implement
        pass
