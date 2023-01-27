import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import git

from album.api import Album
from album.ci.argument_parsing import main
from album.core.controller.album_controller import AlbumController
from album.core.model.catalog import Catalog
from album.core.utils.operations.git_operations import checkout_branch
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.unit.test_unit_core_common import EmptyTestClass


class TestIntegrationCIFeatures(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()
        self.name = "test_catalog"
        self.src, _ = self.setup_empty_catalog(self.name, catalog_type="request")
        self.path = Path(self.tmp_dir.name).joinpath("test_catalog_repo_clone")
        self.repo = None

    def tearDown(self) -> None:
        if self.repo:
            self.repo.close()
        super().tearDown()

    def deploy_request(self):
        catalog_cache_path = Path(self.tmp_dir.name).joinpath("test_catalog_cache")
        self._catalog = Catalog(
            None,
            name=self.name,
            path=catalog_cache_path,
            src=self.src,
            catalog_type="request",
        )

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
            "--ci-user-email=myCiUserEmail",
        ]

        # run
        with patch("album.ci.argument_parsing.create_album_instance") as p:
            p.return_value = Album(
                AlbumController(base_cache_path=Path(self.tmp_dir.name))
            )
            self.assertIsNone(main())
        repo = git.Repo(self.path)
        self.assertEqual("myCiUserName", repo.config_reader().get_value("user", "name"))
        self.assertEqual(
            "myCiUserEmail", repo.config_reader().get_value("user", "email")
        )
        repo.close()

    def test_configure_ssh(self):
        # gather arguments
        sys.argv = [
            "",
            "configure-ssh",
            self.name,
            str(self.path),
            str(self.src),
            "--ci-project-path=myGitGroup/myTestCatalog",
        ]

        # run
        with patch("album.ci.argument_parsing.create_album_instance") as p:
            p.return_value = Album(
                AlbumController(base_cache_path=Path(self.tmp_dir.name))
            )
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
        sys.argv = [
            "",
            "upload",
            self.name,
            str(self.path),
            str(self.src),
            "--branch-name=%s" % branch_name,
        ]

        # run
        with patch("album.ci.argument_parsing.create_album_instance") as p:
            p.return_value = Album(
                AlbumController(base_cache_path=Path(self.tmp_dir.name))
            )
            self.assertIsNone(main())

    @patch("album.ci.controller.zenodo_manager.ZenodoManager.zenodo_get_deposit")
    @patch("album.ci.controller.zenodo_manager.ZenodoManager.zenodo_upload")
    @patch(
        "album.ci.controller.release_manager.ReleaseManager._prepare_zenodo_arguments",
        return_value=("url", "token"),
    )
    def test_prepare_zenodo_upload(
        self, _prepare_zenodo_arguments, zenodo_upload, zenodo_get_deposit
    ):
        # mock
        deposit = EmptyTestClass()
        deposit.id = "id"
        deposit.files = []
        deposit.metadata = EmptyTestClass()
        deposit.metadata.prereserve_doi = {}
        deposit.metadata.prereserve_doi["doi"] = "doi"
        zenodo_get_deposit.return_value = deposit

        # deploy request to test catalog
        branch_name = self.deploy_request()

        # gather arguments
        sys.argv = [
            "",
            "upload",
            self.name,
            str(self.path),
            str(self.src),
            "--branch-name=%s" % branch_name,
        ]

        # run
        with patch("album.ci.argument_parsing.create_album_instance") as p:
            p.return_value = Album(
                AlbumController(base_cache_path=Path(self.tmp_dir.name))
            )
            self.assertIsNone(main())

        self.assertEqual(3, zenodo_upload.call_count)
        solution_dir = Path("solutions", "group", "name")
        self.assertTrue(
            str(zenodo_upload.call_args_list[0][0][1]).endswith(
                str(solution_dir.joinpath("solution.yml"))
            )
        )
        self.assertTrue(
            str(zenodo_upload.call_args_list[1][0][1]).endswith("solution.zip")
        )
        self.assertTrue(
            str(zenodo_upload.call_args_list[2][0][1]).endswith(
                str(solution_dir.joinpath("CHANGELOG.md"))
            )
        )

    def test_update_index(self):
        # deploy request to test catalog
        branch_name = self.deploy_request()

        # gather arguments
        sys.argv = [
            "",
            "update",
            self.name,
            str(self.path),
            str(self.src),
            "--branch-name=%s" % branch_name,
        ]

        # run
        with patch("album.ci.argument_parsing.create_album_instance") as p:
            p.return_value = Album(
                AlbumController(base_cache_path=Path(self.tmp_dir.name))
            )
            self.assertIsNone(main())

        # assert
        self.assertEqual(self.repo.active_branch.name, "group_name_0.1.0")
        self.assertListEqual(
            ["album_catalog_index.db", "album_solution_list.json"],
            self.repo.untracked_files,
        )

    def test_commit_changes(self):
        # deploy request to test catalog
        branch_name = self.deploy_request()

        # checkout this branch
        head = checkout_branch(self.repo, branch_name)

        # save commit message
        self.assertEqual("Adding new/updated group_name_0.1.0\n", head.commit.message)

        # change deployed files so another commit is possible
        with open(
            self.path.joinpath("solutions", "group", "name", "solution.yml"), "a"
        ) as f:
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
            "--ci-user-email=myCiUserEmail",
        ]

        # run
        with patch("album.ci.argument_parsing.create_album_instance") as p:
            p.return_value = Album(
                AlbumController(base_cache_path=Path(self.tmp_dir.name))
            )
            self.assertIsNone(main())

        # check out last commit
        self.assertEqual(self.repo.active_branch.name, "group_name_0.1.0")
        self.assertEqual(
            'Prepared branch "group_name_0.1.0" for merging.\n',
            self.repo.active_branch.commit.message,
        )

    @unittest.skip("Needs to be implemented!")
    def test_merge(self):
        # todo: implement
        pass
