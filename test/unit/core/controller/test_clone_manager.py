import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from git import GitCommandError

import album
from album.core.utils.operations.git_operations import (
    create_bare_repository,
    clone_repository)
from album.core.utils.operations.file_operations import create_path_recursively
from album.core.model.resolve_result import ResolveResult
from test.unit.test_unit_core_common import TestUnitCoreCommon


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

    @unittest.skip("Needs to be implemented!")
    def test__try_cloning_catalog_template(self):
        # todo: implement
        pass

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_valid_url(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = _copy_template_into_repository

        # prepare
        git_https_url = "https://gitlab.com/album-app/album.git"

        # call
        self.clone_manager.setup_repository_from_template(git_https_url, self.tmp_dir.name, "test_catalog")

        # assert
        _copy_template_into_repository.assert_called_once()

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_valid_ssh(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = _copy_template_into_repository

        # prepare
        git_https_url = "git@gitlab.com:album-app/album.git"

        # call
        #with patch("album.core.utils.operations.git_operations.clone_repository") as git_clone_mock:
        self.clone_manager.setup_repository_from_template(git_https_url, self.tmp_dir.name, "test_catalog")

        # assert
        _copy_template_into_repository.assert_called_once()

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_valid_ssh_2(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = _copy_template_into_repository

        # prepare
        git_https_url = "ssh://git@gitlab.com:album-app/album.git"

        # call
        self.clone_manager.setup_repository_from_template(git_https_url, self.tmp_dir.name, "test_catalog")

        # assert
        _copy_template_into_repository.assert_called_once()

    def test_setup_repository_from_template_with_invalid_ssh(self):
        # prepare
        git_https_url = "git@valid_ssh:format.git"

        # call and assert
        with self.assertRaises(GitCommandError):
            self.clone_manager.setup_repository_from_template(git_https_url, self.tmp_dir.name, "test_catalog")

    @patch("album.core.controller.clone_manager.clone_repository")
    def test_setup_repository_from_template_with_local_path(self, git_clone_mock):
        # mocks
        _copy_template_into_repository = MagicMock()
        self.clone_manager._copy_template_into_repository = _copy_template_into_repository

        create_bare_repository = MagicMock()
        album.core.controller.clone_manager.create_bare_repository = create_bare_repository

        create_path_recursively = MagicMock()
        album.core.controller.clone_manager.create_path_recursively = create_path_recursively

        # call
        self.clone_manager.setup_repository_from_template(Path(self.tmp_dir.name), self.tmp_dir.name, Path(self.tmp_dir.name).joinpath("test"), "test_catalog")

        # assert
        _copy_template_into_repository.assert_called_once()
        create_bare_repository.assert_called_once()
        create_path_recursively.assert_called_once()


