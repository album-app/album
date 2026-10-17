import unittest
import zipfile
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock, patch

from git import GitCommandError

import album
from album.core.model.default_values import DefaultValues
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import (
    folder_empty,
)


class TestCondaManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_solution_no_env()
        self.clone_manager = self.album_controller.clone_manager()
        self.catalog = self.setup_empty_catalog("test_catalog")

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_clone(self):
        # todo: implement
        pass

    def test_clone_template(self):
        # mocks
        _clone_catalog_template = MagicMock(return_value=True)
        self.clone_manager._clone_catalog_template = _clone_catalog_template

        # call
        self.clone_manager.clone(
            "template:catalog", self.tmp_dir.name, "test_catalog", "mail", "user"
        )

        # assert
        _clone_catalog_template.assert_called_once_with(
            "catalog", Path(self.tmp_dir.name), "test_catalog", "mail", "user"
        )

    @patch("album.core.controller.clone_manager.download_resource")
    @patch("album.core.controller.clone_manager.is_downloadable", return_value=False)
    def test_clone_template_not_downloadable(
        self, is_downloadable_mock, download_resource_mock
    ):
        # call and assert
        with self.assertRaises(LookupError) as context:
            self.clone_manager.clone(
                "template:unknown-template", self.tmp_dir.name, "test_catalog"
            )

        self.assertIn("unknown-template", str(context.exception))
        self.assertIn(DefaultValues.catalog_template_url.value, str(context.exception))
        is_downloadable_mock.assert_called_once()
        download_resource_mock.assert_not_called()

    def test_clone_template_resolve_error(self):
        # mocks
        cause = ValueError("invalid template")
        self.clone_manager._clone_catalog_template = MagicMock(side_effect=cause)

        # call and assert
        with self.assertRaises(LookupError) as context:
            self.clone_manager.clone(
                "template:broken-template", self.tmp_dir.name, "test_catalog"
            )

        self.assertIn("broken-template", str(context.exception))
        self.assertIn(DefaultValues.catalog_template_url.value, str(context.exception))
        self.assertIs(context.exception.__cause__, cause)

    @patch("album.core.controller.clone_manager.download_resource")
    @patch("album.core.controller.clone_manager.is_downloadable", return_value=True)
    def test__clone_catalog_template_removes_download(self, _, download_resource_mock):
        # mocks
        def download_resource(url, target):
            with zipfile.ZipFile(target, "w") as zip_file:
                zip_file.writestr("catalog-main/README.md", "a template")
            return target

        download_resource_mock.side_effect = download_resource
        template_folders = []

        def setup_repository_from_template(target_path, template_folder, *args):
            self.assertTrue(template_folder.joinpath("README.md").exists())
            template_folders.append(template_folder)

        self.clone_manager.setup_repository_from_template = MagicMock(
            side_effect=setup_repository_from_template
        )

        # call
        self.assertTrue(
            self.clone_manager._clone_catalog_template(
                "catalog", Path(self.tmp_dir.name).joinpath("target"), "test_catalog"
            )
        )

        # assert - the catalog was set up from the template, its download is gone
        self.assertEqual(1, len(template_folders))
        self.assertFalse(template_folders[0].exists())
        self.assertTrue(
            folder_empty(self.album_controller.configuration().cache_path_download())
        )

    @patch("album.core.controller.clone_manager.copy_folder", return_value=False)
    def test__clone_solution(self, copy_folder_mock):
        # create mocks
        resolve_result = ResolveResult(
            path=Path("tmp_dir").joinpath("resolving"),
            catalog=None,
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
        )

        resolve = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve = resolve

        # call
        p = Path("mypath_to").joinpath("solution")
        t = Path("mytarget").joinpath("def")
        self.clone_manager._clone_solution(p, t)

        # assert
        copy_folder_mock.assert_called_once_with(
            Path("tmp_dir"), t, copy_root_folder=False
        )

    def test__clone_solution_leaves_out_files_written_by_deploy(self):
        # a solution as deployed to a catalog
        deployed = Path(self.tmp_dir.name).joinpath("deployed")
        deployed.mkdir()
        for name in [
            "solution.py",
            "environment.yml",
            "CHANGELOG.md",
            "solution.yml",
            "solution.environment.yml",
            "solution.conda-lock.yml",
            "solution.resources.yml",
        ]:
            deployed.joinpath(name).write_text(name)
        resolve_result = ResolveResult(
            path=deployed.joinpath("solution.py"),
            catalog=None,
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
        )
        self.album_controller.collection_manager().resolve = MagicMock(
            return_value=resolve_result
        )
        target = Path(self.tmp_dir.name).joinpath("new-solution")

        # call
        self.clone_manager._clone_solution(deployed, target)

        # assert: the new solution gets its own when it is deployed
        self.assertCountEqual(
            ["solution.py", "environment.yml", "CHANGELOG.md"],
            [p.name for p in target.iterdir()],
        )

    @unittest.skip("Needs to be implemented!")
    def test__try_cloning_catalog_template(self):
        # todo: implement
        pass

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_valid_url(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = (
            _copy_template_into_repository
        )

        # prepare
        git_https_url = "https://gitlab.com/album-app/album.git"

        # call
        self.clone_manager.setup_repository_from_template(
            git_https_url, self.tmp_dir.name, "test_catalog"
        )

        # assert
        _copy_template_into_repository.assert_called_once()

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_valid_ssh(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = (
            _copy_template_into_repository
        )

        # prepare
        git_https_url = "git@gitlab.com:album-app/album.git"

        # call
        # with patch("album.core.utils.operations.git_operations.clone_repository") as git_clone_mock:
        self.clone_manager.setup_repository_from_template(
            git_https_url, self.tmp_dir.name, "test_catalog"
        )

        # assert
        _copy_template_into_repository.assert_called_once()

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_valid_ssh_2(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = (
            _copy_template_into_repository
        )

        # prepare
        git_https_url = "ssh://git@gitlab.com:album-app/album.git"

        # call
        self.clone_manager.setup_repository_from_template(
            git_https_url, self.tmp_dir.name, "test_catalog"
        )

        # assert
        _copy_template_into_repository.assert_called_once()

    def test_setup_repository_from_template_with_invalid_ssh(self):
        # prepare
        git_https_url = "git@valid_ssh:format.git"

        # call and assert
        with self.assertRaises(GitCommandError):
            self.clone_manager.setup_repository_from_template(
                git_https_url, self.tmp_dir.name, "test_catalog"
            )

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_local_path(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = (
            _copy_template_into_repository
        )

        create_bare_repository = MagicMock()
        album.core.controller.clone_manager.create_bare_repository = (
            create_bare_repository
        )

        create_path_recursively = MagicMock()
        album.core.controller.clone_manager.create_path_recursively = (
            create_path_recursively
        )

        # call
        self.clone_manager.setup_repository_from_template(
            Path(self.tmp_dir.name),
            self.tmp_dir.name,
            Path(self.tmp_dir.name).joinpath("test"),
            "test_catalog",
        )

        # assert
        _copy_template_into_repository.assert_called_once()
        create_bare_repository.assert_called_once()
        create_path_recursively.assert_called_once()
