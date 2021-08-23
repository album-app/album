import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from album.core.model.default_values import DefaultValues

from album.ci.utils.zenodo_api import ZenodoAPI
from album.core.controller.deploy_manager import DeployManager
from album.core.model.group_name_version import GroupNameVersion
from test.unit.test_unit_common import TestGitCommon


class TestDeployManager(TestGitCommon):
    def setUp(self) -> None:
        super().setUp()
        self.zenodoAPI = ZenodoAPI('url', 'access_token')
        self.create_test_config()
        self.create_test_solution_no_env()
        self.create_test_catalog_manager()

        # add remote catalog
        self.collection_manager.catalogs().add_by_src(DefaultValues.default_catalog_src.value)

        # add local catalog
        catalog_path = Path(self.tmp_dir.name).joinpath("local_catalog")
        catalog_path.mkdir(parents=True)
        with open(catalog_path.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as meta:
            meta.writelines("{\"name\":\"local_catalog\", \"version\": \"0.1.0\"}")
        self.local_catalog = self.collection_manager.catalogs().add_by_src(catalog_path)

        self.deploy_manager = DeployManager()

    def tearDown(self) -> None:
        super().tearDown()

    @patch('album.core.controller.deploy_manager.load')
    @patch('album.core.model.catalog.download_repository')
    def test_deploy_catalog_name_given_and_local(self, download_catalog, load_mock):

        # mocks
        load_mock.return_value = self.active_solution

        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.deploy_manager._copy_and_zip = _copy_and_zip

        _copy_cover_to_local_src = MagicMock(return_value=["cover1", "cover2"])
        self.deploy_manager._copy_cover_to_local_src = _copy_cover_to_local_src

        _create_yaml_file_in_local_src = MagicMock(return_value="copiedYmlFilePath")
        self.deploy_manager._create_yaml_file_in_local_src = _create_yaml_file_in_local_src

        _create_merge_request = MagicMock(return_value=None)
        self.deploy_manager._create_merge_request = _create_merge_request

        get_catalog_by_id = MagicMock(return_value=self.local_catalog)
        self.collection_manager.catalogs().get_by_name = get_catalog_by_id

        get_catalog_by_src = MagicMock(return_value=None)
        self.collection_manager.catalogs().get_by_src = get_catalog_by_src

        # call
        self.deploy_manager.collection_manager = self.collection_manager
        self.deploy_manager.deploy(deploy_path="None",
                                   catalog_name=os.path.basename(self.tmp_dir.name),
                                   dry_run=False,
                                   trigger_pipeline=False)

        # assert
        self.assertEqual(self.local_catalog, self.deploy_manager._catalog)  # correct catalog chosen
        get_catalog_by_id.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_catalog_by_src.assert_not_called()  # catalog given by id not url
        _copy_and_zip.called_once()  # remote -> zip to repo
        _copy_cover_to_local_src.called_once()  # remote -> cover outside zip
        _create_yaml_file_in_local_src.called_once()  # local -> no yaml
        _create_merge_request.assert_not_called()  # local -> no merge request
        download_catalog.assert_not_called()  # local -> no download

    @patch('album.core.controller.deploy_manager.load')
    @patch('album.core.model.catalog.Catalog.retrieve_catalog_meta_information', return_value={"name": "", "version": "0.1.0"})
    def test_deploy_catalog_in_active_solution(self, catalog_meta, load_mock):

        deploy_catalog = self.collection_manager.catalogs().get_all()[1]

        # mocks
        load_mock.return_value = self.active_solution

        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.deploy_manager._copy_and_zip = _copy_and_zip

        _copy_cover_to_local_src = MagicMock(return_value=["cover1", "cover2"])
        self.deploy_manager._copy_cover_to_local_src = _copy_cover_to_local_src

        _create_yaml_file_in_local_src = MagicMock(return_value="copiedYmlFilePath")
        self.deploy_manager._create_yaml_file_in_local_src = _create_yaml_file_in_local_src

        _create_merge_request = MagicMock(return_value=None)
        self.deploy_manager._create_merge_request = _create_merge_request

        update_repo = MagicMock(side_effect=lambda repo: repo)
        self.deploy_manager._update_repo = update_repo

        download_catalog = MagicMock(return_value="aRepository")
        deploy_catalog.retrieve_catalog = download_catalog

        get_catalog_by_src = MagicMock(return_value=deploy_catalog)
        self.collection_manager.catalogs().get_by_src = get_catalog_by_src

        get_catalog_by_id = MagicMock(None)
        self.collection_manager.catalogs().get_by_name = get_catalog_by_id

        # call
        self.active_solution.__setattr__("deploy", {
            "catalog": {"src": DefaultValues.default_catalog_src.value}
        })
        self.deploy_manager.collection_manager = self.collection_manager
        self.deploy_manager.deploy(deploy_path="myPath",
                                   catalog_name=None,
                                   dry_run=False,
                                   trigger_pipeline=False)

        # assert
        self.assertEqual(deploy_catalog, self.deploy_manager._catalog)  # correct catalog chosen
        get_catalog_by_src.assert_called_once_with(DefaultValues.default_catalog_src.value)  # correct url requested
        get_catalog_by_id.assert_not_called()  # catalog given by url, not id
        download_catalog.assert_called_once()  # remote -> download
        catalog_meta.assert_called_once()  # remote -> download
        _copy_and_zip.assert_called_once_with(Path("myPath"))  # remote -> zip to repo
        _copy_cover_to_local_src.assert_called_once_with(Path("myPath"))  # remote -> cover outside zip
        _create_yaml_file_in_local_src.assert_called_once_with()  # remote -> create yaml
        _create_merge_request.assert_called_once_with(  # remote -> create MR
            ["copiedYmlFilePath", "solution_zip"] + ["cover1", "cover2"], False, False, None, None
        )

    @patch('album.core.controller.deploy_manager.load')
    def test_deploy_catalog_not_given(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.deploy_manager._copy_and_zip = _copy_and_zip

        _copy_cover_to_local_src = MagicMock(return_value=["cover1", "cover2"])
        self.deploy_manager._copy_cover_to_local_src = _copy_cover_to_local_src

        _create_yaml_file_in_local_src = MagicMock(return_value="copiedYmlFilePath")
        self.deploy_manager._create_yaml_file_in_local_src = _create_yaml_file_in_local_src

        _create_solution_merge_request = MagicMock(return_value=None)
        self.deploy_manager._create_merge_request = _create_solution_merge_request

        get_catalog_by_src = MagicMock(return_value=self.collection_manager.catalogs().get_local_catalog())
        self.collection_manager.catalogs().get_by_src = get_catalog_by_src

        get_catalog_by_id = MagicMock(None)
        self.collection_manager.catalogs().get_by_name = get_catalog_by_id

        # call
        self.deploy_manager.collection_manager = self.collection_manager
        with self.assertRaises(RuntimeError):
            self.deploy_manager.deploy(deploy_path="myPath",
                                       catalog_name=None,
                                       dry_run=False,
                                       trigger_pipeline=False)

    def test_retrieve_head_name(self):
        self.deploy_manager.collection_manager = self.collection_manager
        self.deploy_manager._active_solution = self.active_solution

        self.assertEqual("tsg_tsn_tsv", self.deploy_manager.retrieve_head_name())

    @patch('album.core.controller.deploy_manager.add_files_commit_and_push', return_value=True)
    def test__create_merge_request(self, add_files_commit_and_push_mock):
        self.create_tmp_repo()

        self.deploy_manager.collection_manager = self.collection_manager
        self.deploy_manager._repo = self.repo
        self.deploy_manager._active_solution = self.active_solution

        self.deploy_manager._create_merge_request([self.closed_tmp_file.name], dry_run=True)

        add_files_commit_and_push_mock.assert_called_once_with(
            self.repo.heads[1], [self.closed_tmp_file.name],
            "Adding new/updated tsg_tsn_tsv", False, True, None,
            None
        )

    @patch('album.core.model.album_base.AlbumClass.get_deploy_dict')
    def test__create_yaml_file_in_local_src(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        self.create_tmp_repo()

        self.deploy_manager._catalog = self.collection_manager.catalogs().get_all()[0]
        self.deploy_manager._repo = self.deploy_manager._update_repo(self.repo)
        self.deploy_manager._active_solution = self.active_solution

        y_path = self.deploy_manager._create_yaml_file_in_local_src()

        self.assertEqual(Path(self.repo.working_tree_dir).joinpath("catalog", "tsg", "tsn", "tsv", "tsn.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)

    @patch('album.core.model.album_base.AlbumClass.get_deploy_dict')
    def test__get_cache_suffix(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        # prepare
        self.create_tmp_repo()
        self.deploy_manager._repo = self.deploy_manager._update_repo(self.repo)
        self.deploy_manager._active_solution = self.active_solution
        self.deploy_manager._catalog = self.collection_manager.catalogs().get_local_catalog()

        result = Path(self.repo.working_tree_dir).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv",
            "_".join(["tsg", "tsn", "tsv"]) + ".zip"
        )

        self.assertEqual(result, self.deploy_manager._get_cache_suffix())

    @patch('album.core.controller.deploy_manager.copy', return_value="absPathCopyOfCover")
    def test__copy_cover_to_local_src(self, copy_mock):
        # set covers
        self.active_solution["covers"] = ["example_cover1.png", "example_cover2.png"]

        # prepare fake covers and solution_file
        Path(self.tmp_dir.name).joinpath("example_cover1.png").touch()
        Path(self.tmp_dir.name).joinpath("example_cover2.png").touch()
        Path(self.tmp_dir.name).joinpath(DefaultValues.solution_default_name.value).touch()

        self.create_tmp_repo()
        self.deploy_manager._repo = self.deploy_manager._update_repo(self.repo)
        self.deploy_manager._active_solution = self.active_solution
        self.deploy_manager._catalog = self.collection_manager.catalogs().get_local_catalog()

        tmp_dir = Path(self.tmp_dir.name)
        target_dir = Path(self.repo.working_tree_dir).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv"
        )

        # assert
        self.assertEqual(["absPathCopyOfCover", "absPathCopyOfCover"], self.deploy_manager._copy_cover_to_local_src(tmp_dir))

        calls = [call(tmp_dir.joinpath("example_cover1.png"), target_dir.joinpath("example_cover1.png")),
                 call(tmp_dir.joinpath("example_cover2.png"), target_dir.joinpath("example_cover2.png"))]
        copy_mock.assert_has_calls(calls)

    @patch('album.core.controller.deploy_manager.zip_folder', return_value="absPathZipFile")
    @patch('album.core.controller.deploy_manager.zip_paths', return_value="absPathZipFile")
    def test__copy_and_zip(self, zip_path_mock, zip_folder):
        self.create_tmp_repo()
        self.deploy_manager._repo = self.deploy_manager._update_repo(self.repo)
        self.deploy_manager._active_solution = self.active_solution
        self.deploy_manager._catalog = self.collection_manager.catalogs().get_local_catalog()

        solution_folder_to_deploy_locally = Path(self.tmp_dir.name)
        solution_file_to_deploy_locally = Path(self.tmp_dir.name).joinpath("nice_file.py")
        solution_file_to_deploy_locally.touch()

        # result
        r = Path(self.repo.working_tree_dir).joinpath(
            self.collection_manager.catalogs().get_local_catalog().get_solution_zip_suffix(GroupNameVersion("tsg", "tsn", "tsv"))
        )

        # copy and zip a folder
        self.deploy_manager._copy_and_zip(solution_folder_to_deploy_locally)
        zip_folder.assert_called_once_with(solution_folder_to_deploy_locally, r)
        zip_path_mock.assert_not_called()

        # reset
        zip_path_mock.reset_mock()
        zip_folder.reset_mock()

        # copy and zip a file
        self.deploy_manager._copy_and_zip(solution_file_to_deploy_locally)
        zip_path_mock.assert_called_once()
        zip_folder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
