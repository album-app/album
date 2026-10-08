from pathlib import Path
from test.unit.test_unit_core_common import (
    EmptyTestClass,
    TestCatalogAndCollectionCommon,
    TestGitCommon,
)
from unittest.mock import MagicMock, patch

import git

from album.core.controller.deploy_manager import DeployManager
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.runner.core.model.coordinates import Coordinates


class TestDeployManager(TestGitCommon, TestCatalogAndCollectionCommon):
    def setUp(self) -> None:
        super().setUp()
        self.setup_solution_no_env()
        self.meta_file_content = self.get_catalog_meta_dict()
        self.deploy_manager = self.album_controller.deploy_manager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_deploy(
        self,
    ):
        # mock
        _get_path_to_solution = MagicMock(return_value="solutionPath")
        self.deploy_manager._get_path_to_solution = _get_path_to_solution

        load = MagicMock(return_value=self.active_solution)
        self.album_controller.state_manager().load = load

        get_by_name = MagicMock(return_value="myCatalogLoaded")
        self.album_controller.catalogs().get_by_name = get_by_name

        _deploy = MagicMock(return_value=None)
        self.deploy_manager._deploy = _deploy

        # call
        self.deploy_manager.deploy("deployPath", "catName", False, changelog="asd")

        # assert
        _get_path_to_solution.assert_called_once_with(Path("deployPath"))
        load.assert_called_once_with("solutionPath")
        get_by_name.assert_called_once_with("catName")
        _deploy.assert_called_once_with(
            "myCatalogLoaded",
            self.active_solution,
            Path("deployPath"),
            False,
            False,
            [],
            "",
            "",
            False,
        )

    @patch(
        "album.core.controller.deploy_manager.process_changelog_file",
        return_value="Chanelog",
    )
    def test__deploy_direct(self, process_changelog_file):
        catalog_src_path, catalog_clone_path = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )
        catalog._type = "direct"

        # mock
        retrieve_catalog = MagicMock(return_value=git.Repo(catalog_clone_path))
        catalog.retrieve_catalog = retrieve_catalog

        _deploy_to_direct_catalog = MagicMock()
        self.deploy_manager._deploy_to_direct_catalog = _deploy_to_direct_catalog

        _deploy_to_request_catalog = MagicMock()
        self.deploy_manager._deploy_to_request_catalog = _deploy_to_request_catalog

        # call
        self.deploy_manager._deploy(
            catalog, self.active_solution, "deployPath", False, False, None
        )

        # assert
        process_changelog_file.assert_called_once_with(
            catalog, self.active_solution, "deployPath"
        )
        retrieve_catalog.assert_called_once()
        _deploy_to_direct_catalog.assert_called_once()
        _deploy_to_request_catalog.assert_not_called()

    @patch(
        "album.core.controller.deploy_manager.process_changelog_file",
        return_value="Chanelog",
    )
    def test__deploy_request(self, process_changelog_file):
        catalog_src_path, catalog_clone_path = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )
        catalog._type = "request"

        # mock
        retrieve_catalog = MagicMock(return_value=git.Repo(catalog_clone_path))
        catalog.retrieve_catalog = retrieve_catalog

        _deploy_to_direct_catalog = MagicMock()
        self.deploy_manager._deploy_to_direct_catalog = _deploy_to_direct_catalog

        _deploy_to_request_catalog = MagicMock()
        self.deploy_manager._deploy_to_request_catalog = _deploy_to_request_catalog

        # call
        self.deploy_manager._deploy(
            catalog, self.active_solution, "myDeployPath", False, False, None
        )

        # assert
        process_changelog_file.assert_called_once_with(
            catalog, self.active_solution, "myDeployPath"
        )
        retrieve_catalog.assert_called_once()
        _deploy_to_direct_catalog.assert_not_called()
        _deploy_to_request_catalog.assert_called_once()

    def test__deploy_request_wrong_type(self):
        catalog_src_path, _ = self.setup_empty_catalog("test_cat")
        catalog = Catalog(
            0,
            "test_cat",
            src=catalog_src_path,
            path=Path(self.tmp_dir.name).joinpath("catalog_cache_path"),
        )
        catalog._type = "typeDoesNotExist"

        with self.assertRaises(RuntimeError):
            self.deploy_manager._deploy(
                catalog, self.active_solution, "myDeployPath", False, False, None
            )

    def _setup_undeploy_mocks(self, index_versions):
        repo = EmptyTestClass()
        repo.working_tree_dir = self.tmp_dir.name
        Path(self.tmp_dir.name).joinpath(
            DefaultValues.catalog_index_metafile_json.value
        ).touch()

        catalog = MagicMock()
        catalog.get_meta_file_path.return_value = Path(self.tmp_dir.name).joinpath(
            "cache", DefaultValues.catalog_index_metafile_json.value
        )
        catalog.name.return_value = "test_cat"
        catalog.is_cache.return_value = False
        catalog.retrieve_catalog.return_value.__enter__.return_value = repo
        catalog.index.return_value.get_all_solution_versions.return_value = [
            {"group": "grp", "name": "seg", "version": v} for v in index_versions
        ]
        self.album_controller.catalogs().get_by_name = MagicMock(return_value=catalog)
        self.album_controller.migration_manager().load_index = MagicMock()
        self.album_controller.migration_manager().refresh_index = MagicMock()

        self.deploy_manager._remove_db_entry_and_files = MagicMock()
        self.deploy_manager._remove_db_entry_and_revert_files = MagicMock()
        self.deploy_manager._remove_db_entry_and_tag = MagicMock()

        return repo, catalog

    @patch("album.core.controller.deploy_manager.get_tags")
    def test_undeploy_only_version_ignores_prefix_sharing_solution(self, get_tags):
        # the tag of "grp-seg-tools" is newer than the only tag of "grp-seg"
        get_tags.return_value = ["grp-seg-tools-1.0.0", "grp-seg-1.0.0"]
        repo, catalog = self._setup_undeploy_mocks(["1.0.0"])

        # call
        self.deploy_manager.undeploy("grp:seg:1.0.0", "test_cat", False)

        # assert: no previous version, so files and db entry are removed
        coordinates = Coordinates("grp", "seg", "1.0.0")
        catalog.remove.assert_called_once_with(coordinates)
        self.deploy_manager._remove_db_entry_and_files.assert_called_once_with(
            repo, coordinates, False, [], "", ""
        )
        self.deploy_manager._remove_db_entry_and_revert_files.assert_not_called()
        self.deploy_manager._remove_db_entry_and_tag.assert_not_called()

    @patch("album.core.controller.deploy_manager.get_tags")
    def test_undeploy_current_version_reverts_to_previous(self, get_tags):
        get_tags.return_value = [
            "grp-seg-tools-1.0.0",
            "grp-seg-1.0.0",
            "grp-seg-0.9.0",
        ]
        repo, _ = self._setup_undeploy_mocks(["1.0.0", "0.9.0"])

        # call
        self.deploy_manager.undeploy("grp:seg:1.0.0", "test_cat", False)

        # assert
        self.deploy_manager._remove_db_entry_and_revert_files.assert_called_once_with(
            repo,
            Coordinates("grp", "seg", "1.0.0"),
            "grp-seg-0.9.0",
            False,
            [],
            "",
            "",
        )
        self.deploy_manager._remove_db_entry_and_files.assert_not_called()
        self.deploy_manager._remove_db_entry_and_tag.assert_not_called()

    @patch("album.core.controller.deploy_manager.get_tags")
    def test_undeploy_previous_version_removes_tag_only(self, get_tags):
        get_tags.return_value = [
            "grp-seg-tools-1.0.0",
            "grp-seg-1.0.0",
            "grp-seg-0.9.0",
        ]
        repo, _ = self._setup_undeploy_mocks(["1.0.0", "0.9.0"])

        # call
        self.deploy_manager.undeploy("grp:seg:0.9.0", "test_cat", False)

        # assert
        self.deploy_manager._remove_db_entry_and_tag.assert_called_once_with(
            repo, Coordinates("grp", "seg", "0.9.0"), False, [], "", ""
        )
        self.deploy_manager._remove_db_entry_and_files.assert_not_called()
        self.deploy_manager._remove_db_entry_and_revert_files.assert_not_called()

    @patch("album.core.controller.deploy_manager.get_tags")
    def test_undeploy_unknown_version(self, get_tags):
        get_tags.return_value = ["grp-seg-tools-1.0.0", "grp-seg-1.0.0"]
        self._setup_undeploy_mocks(["1.0.0"])

        with self.assertRaises(LookupError):
            self.deploy_manager.undeploy("grp:seg:0.9.0", "test_cat", False)

        self.deploy_manager._remove_db_entry_and_files.assert_not_called()
        self.deploy_manager._remove_db_entry_and_revert_files.assert_not_called()
        self.deploy_manager._remove_db_entry_and_tag.assert_not_called()

    def test__deploy_to_direct_catalog(self):
        # prepare
        catalog = EmptyTestClass()
        catalog.src = lambda: "mySrc"
        catalog.index_file_path = lambda: "indexSrcPath"

        repo = EmptyTestClass()
        repo.working_tree_dir = "myWorkingDir"

        # mock
        _add_to_downloaded_catalog = MagicMock()
        self.deploy_manager._add_to_downloaded_catalog = _add_to_downloaded_catalog

        _deploy_routine_in_local_src = MagicMock(return_value=(["export1", "export2"]))
        self.deploy_manager._deploy_routine_in_local_src = _deploy_routine_in_local_src

        _push_directly = MagicMock()
        self.deploy_manager._push_directly = _push_directly

        refresh_index = MagicMock()
        self.album_controller.migration_manager().refresh_index = refresh_index

        # call
        self.deploy_manager._deploy_to_direct_catalog(
            repo,
            catalog,
            self.active_solution,
            "deployPath",
            False,
            True,
            None,
            "myEmail",
            "myName",
        )

        # assert
        _add_to_downloaded_catalog.assert_called_once_with(
            catalog, self.active_solution, False, True
        )
        _deploy_routine_in_local_src.assert_called_once_with(
            catalog, repo, self.active_solution, "deployPath", False
        )
        _push_directly.assert_called_once_with(
            self.active_solution.coordinates(),
            repo,
            [str(Path("solutions", "tsg", "tsn"))],
            ["export1", "export2", "indexSrcPath"],
            False,
            None,
            "myEmail",
            "myName",
            tag="tsg-tsn-tsv",
        )
        refresh_index.assert_not_called()

    @patch(
        "album.core.controller.deploy_manager.retrieve_default_mr_push_options",
        return_value="pushOptions",
    )
    def test__deploy_to_request_catalog(self, retrieve_default_mr_push_options):
        # prepare
        repo = EmptyTestClass()
        repo.working_tree_dir = "myWorkingDir"

        catalog = EmptyTestClass()
        catalog.src = lambda: "mySrc"

        # mock
        _deploy_routine_in_local_src = MagicMock(return_value=(["export1", "export2"]))
        self.deploy_manager._deploy_routine_in_local_src = _deploy_routine_in_local_src

        _create_merge_request = MagicMock()
        self.deploy_manager._create_merge_request = _create_merge_request

        # call
        self.deploy_manager._deploy_to_request_catalog(
            repo,
            catalog,
            self.active_solution,
            "deployPath",
            False,
            None,
            "myEmail",
            "myName",
        )

        # assert
        _deploy_routine_in_local_src.assert_called_once_with(
            catalog, repo, self.active_solution, "deployPath", False
        )
        retrieve_default_mr_push_options.assert_called_once_with("mySrc")
        _create_merge_request.assert_called_once_with(
            self.active_solution.coordinates(),
            repo,
            ["export1", "export2"],
            False,
            "pushOptions",
            "myEmail",
            "myName",
            files_to_remove=[str(Path("solutions", "tsg", "tsn"))],
        )

    def test__deploy_routine_in_local_src(self):
        # prepare
        repo = EmptyTestClass()
        repo.working_tree_dir = "myWorkingDir"

        catalog = EmptyTestClass()

        # mock
        _collect_solution_files = MagicMock(return_value="exports")
        self.album_controller.resource_manager().write_solution_files = (
            _collect_solution_files
        )

        # call
        r = self.deploy_manager._deploy_routine_in_local_src(
            catalog, repo, self.active_solution, "deployPath", False
        )

        # assert
        self.assertEqual(r, "exports")

    def test__add_to_downloaded_catalog(self):
        # prepare
        catalog = EmptyTestClass()

        # mock
        add = MagicMock()
        catalog.add = add

        # call
        self.deploy_manager._add_to_downloaded_catalog(
            catalog, self.active_solution, False, True
        )

        # assert
        add.assert_called_once_with(self.active_solution, force_overwrite=True)

    def test__add_to_downloaded_catalog_dry_run(self):
        # prepare
        catalog = EmptyTestClass()

        # mock
        add = MagicMock()
        catalog.add = add

        # call
        self.deploy_manager._add_to_downloaded_catalog(
            catalog, self.active_solution, True, True
        )

        # assert
        add.assert_not_called()

    def test_get_download_path(self):
        # prepare
        catalog = EmptyTestClass()
        catalog.name = lambda: "myCatalogName"

        expected = Path(
            self.album_controller.configuration().cache_path_download()
        ).joinpath("myCatalogName")
        # call & assert
        self.assertEqual(expected, self.deploy_manager.get_download_path(catalog))

    @staticmethod
    def _catalog_knowing_versions(versions):
        catalog = MagicMock()
        catalog.index.return_value.get_all_solution_versions.return_value = [
            {"group": "grp", "name": "seg", "version": v} for v in versions
        ]
        return catalog

    @patch("album.core.controller.deploy_manager.get_tags")
    def test__get_tags_for_coordinates(self, get_tags):
        # tags as get_tags returns them: newest commit first
        get_tags.return_value = [
            "grp-seg-tools-1.0.0",
            "grp-seg-1.0.0",
            "grp-seg-0.9.0",
        ]
        catalog = self._catalog_knowing_versions(["0.9.0", "1.0.0"])
        repo = EmptyTestClass()

        # call
        tags = self.deploy_manager._get_tags_for_coordinates(
            repo, catalog, Coordinates("grp", "seg", "1.0.0")
        )

        # assert: the prefix-sharing solution is ignored, newest version first
        self.assertEqual(["grp-seg-1.0.0", "grp-seg-0.9.0"], tags)
        get_tags.assert_called_once_with(repo)
        catalog.index.return_value.get_all_solution_versions.assert_called_once_with(
            "grp", "seg"
        )

    @patch("album.core.controller.deploy_manager.get_tags")
    def test__get_tags_for_coordinates_version_order(self, get_tags):
        # commit order differs from version order; 2.0.0 is in the index but not
        # tagged; "tsv" is not a PEP 440 version
        get_tags.return_value = [
            "grp-seg-0.9.0",
            "grp-seg-tsv",
            "grp-seg-1.0.0",
            "grp-seg-0.10.0",
            "grp-seg-tools-1.0.0",
        ]
        catalog = self._catalog_knowing_versions(
            ["0.10.0", "0.9.0", "1.0.0", "2.0.0", "tsv"]
        )

        # call
        tags = self.deploy_manager._get_tags_for_coordinates(
            EmptyTestClass(), catalog, Coordinates("grp", "seg", "1.0.0")
        )

        # assert
        self.assertEqual(
            ["grp-seg-1.0.0", "grp-seg-0.10.0", "grp-seg-0.9.0", "grp-seg-tsv"], tags
        )

    @patch("album.core.controller.deploy_manager.get_tags")
    def test__get_tags_for_coordinates_index_not_loaded(self, get_tags):
        catalog = MagicMock()
        catalog.index.return_value = None

        with self.assertRaises(RuntimeError):
            self.deploy_manager._get_tags_for_coordinates(
                EmptyTestClass(), catalog, Coordinates("grp", "seg", "1.0.0")
            )
        get_tags.assert_not_called()

    def test__get_absolute_prefix_path(self):
        # fixme: definitely fix me! smth. is wrong
        pass

    @patch("album.core.controller.deploy_manager.force_remove")
    @patch("album.core.controller.deploy_manager.folder_empty", return_value=False)
    def test__clear_deploy_target_path(self, _, force_remove):
        self.deploy_manager._clear_deploy_target_path(Path(self.tmp_dir.name), True)
        force_remove.assert_called_once()

    @patch("album.core.controller.deploy_manager.force_remove")
    @patch("album.core.controller.deploy_manager.folder_empty", return_value=True)
    def test__clear_deploy_target_path_empty(self, _, force_remove):
        self.deploy_manager._clear_deploy_target_path(Path(self.tmp_dir.name), True)
        force_remove.assert_not_called()

    @patch("album.core.controller.deploy_manager.force_remove")
    @patch("album.core.controller.deploy_manager.folder_empty", return_value=False)
    def test__clear_deploy_target_path_force_false(self, _, __):
        with self.assertRaises(RuntimeError):
            self.deploy_manager._clear_deploy_target_path(
                Path(self.tmp_dir.name), False
            )

    def test__get_path_to_solution(self):
        r = self.deploy_manager._get_path_to_solution(Path(self.tmp_dir.name))
        e = Path(self.tmp_dir.name).joinpath(DefaultValues.solution_default_name.value)
        self.assertEqual(e, r)

    def test__get_path_to_solution_file(self):
        r = self.deploy_manager._get_path_to_solution(Path(self.closed_tmp_file.name))
        self.assertEqual(Path(self.closed_tmp_file.name), r)

    def test_retrieve_head_name(self):
        self.assertEqual(
            "tsg_tsn_tsv",
            DeployManager.retrieve_head_name(Coordinates("tsg", "tsn", "tsv")),
        )

    @patch(
        "album.core.controller.deploy_manager.add_files_commit_and_push",
        return_value=True,
    )
    def test__create_merge_request(self, add_files_commit_and_push_mock):
        with self.setup_tmp_repo() as repo:
            # call
            DeployManager._create_merge_request(
                Coordinates("tsg", "tsn", "tsv"),
                repo,
                [self.closed_tmp_file.name],
                dry_run=True,
            )

            add_files_commit_and_push_mock.assert_called_once_with(
                repo.heads[1],
                [Path(self.closed_tmp_file.name)],
                "Adding new/updated tsg_tsn_tsv",
                email="",
                force=True,
                push=False,
                push_option_list=[],
                username="",
            )

    @patch("album.core.controller.deploy_manager.checkout_main", return_value="head")
    @patch("album.core.controller.deploy_manager.add_files_commit_and_push")
    @patch("album.core.controller.deploy_manager.remove_files")
    def test__push_directly(
        self, remove_files, add_files_commit_and_push, checkout_main
    ):
        repo = EmptyTestClass()
        file_paths = [Path("a"), Path("b"), Path("c")]

        commit_msg = "Adding new/updated tsg_tsn_tsv"

        # call
        self.deploy_manager._push_directly(
            self.active_solution.coordinates(),
            repo,
            [],
            file_paths,
            False,
            None,
            None,
            None,
        )

        # assert
        remove_files.assert_called_once_with("head", [])
        add_files_commit_and_push.assert_called_once_with(
            "head",
            file_paths,
            commit_msg,
            push=True,
            email=None,
            push_option_list=[],
            username=None,
            force=False,
            tag="",
        )
