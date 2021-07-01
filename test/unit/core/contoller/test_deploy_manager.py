import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from hips.core.model.default_values import HipsDefaultValues

from hips.ci.zenodo_api import ZenodoAPI
from hips.core.controller.deploy_manager import DeployManager
from test.unit.test_common import TestGitCommon


class TestDeployManager(TestGitCommon):
    def setUp(self) -> None:
        self.zenodoAPI = ZenodoAPI('url', 'access_token')
        self.create_test_config()
        self.create_test_hips_no_env()

        self.hips_deploy = DeployManager()

    def tearDown(self) -> None:
        super().tearDown()

    @patch('hips.core.controller.deploy_manager.load')
    def test_deploy_catalog_name_given(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        _copy_solution_in_catalog = MagicMock(return_value=None)
        self.hips_deploy._copy_folder_in_local_catalog = _copy_solution_in_catalog

        _copy_folder_in_local_catalog = MagicMock(return_value="copiedSolutionFilePath")
        self.hips_deploy._copy_folder_in_local_catalog = _copy_folder_in_local_catalog

        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.hips_deploy._copy_and_zip = _copy_and_zip

        _copy_cover_to_repo = MagicMock(return_value=["cover1", "cover2"])
        self.hips_deploy._copy_cover_to_repo = _copy_cover_to_repo

        _create_yaml_file_in_repo = MagicMock(return_value="copiedYmlFilePath")
        self.hips_deploy._create_yaml_file_in_repo = _create_yaml_file_in_repo

        _create_hips_merge_request = MagicMock(return_value=None)
        self.hips_deploy._create_hips_merge_request = _create_hips_merge_request

        download_catalog = MagicMock(return_value="aRepository")
        self.test_catalog_collection.catalogs[0].download = download_catalog

        get_catalog_by_id = MagicMock(return_value=self.test_catalog_collection.catalogs[1])
        self.test_catalog_collection.get_catalog_by_id = get_catalog_by_id

        get_catalog_by_url = MagicMock(return_value=None)
        self.test_catalog_collection.get_catalog_by_url = get_catalog_by_url

        # call
        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy.deploy(deploy_path="None",
                                catalog=os.path.basename(self.tmp_dir.name),
                                dry_run=False,
                                trigger_pipeline=False)

        # assert
        self.assertEqual(self.test_catalog_collection.catalogs[1], self.hips_deploy._catalog)  # correct catalog chosen
        get_catalog_by_id.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_catalog_by_url.assert_not_called()  # catalog given by id not url
        _copy_folder_in_local_catalog.assert_called_once_with(Path("None"))  # local ->  copy locally
        _copy_and_zip.assert_not_called()  # remote -> zip to repo
        _copy_cover_to_repo.assert_not_called()  # remote -> cover outside zip
        _create_yaml_file_in_repo.assert_not_called()  # local -> no yaml
        _create_hips_merge_request.assert_not_called()  # local -> no merge request
        download_catalog.assert_not_called()  # local -> no download

    @patch('hips.core.controller.deploy_manager.load')
    def test_deploy_catalog_in_active_hips(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        _copy_solution_in_catalog = MagicMock(return_value=None)
        self.hips_deploy._copy_folder_in_local_catalog = _copy_solution_in_catalog

        _copy_folder_in_local_catalog = MagicMock(return_value="copiedSolutionFilePath")
        self.hips_deploy._copy_folder_in_local_catalog = _copy_folder_in_local_catalog

        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.hips_deploy._copy_and_zip = _copy_and_zip

        _copy_cover_to_repo = MagicMock(return_value=["cover1", "cover2"])
        self.hips_deploy._copy_cover_to_repo = _copy_cover_to_repo

        _create_yaml_file_in_repo = MagicMock(return_value="copiedYmlFilePath")
        self.hips_deploy._create_yaml_file_in_repo = _create_yaml_file_in_repo

        _create_hips_merge_request = MagicMock(return_value=None)
        self.hips_deploy._create_hips_merge_request = _create_hips_merge_request

        download_catalog = MagicMock(return_value="aRepository")
        self.test_catalog_collection.catalogs[0].download = download_catalog

        get_catalog_by_url = MagicMock(return_value=self.test_catalog_collection.catalogs[0])
        self.test_catalog_collection.get_catalog_by_url = get_catalog_by_url

        get_catalog_by_id = MagicMock(None)
        self.test_catalog_collection.get_catalog_by_id = get_catalog_by_id

        # call
        self.active_hips.__setattr__("deploy", {
            "catalog": {"url": HipsDefaultValues.catalog_url.value}
        })
        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy.deploy(deploy_path="myPath",
                                catalog=None,
                                dry_run=False,
                                trigger_pipeline=False)

        # assert
        self.assertEqual(self.test_catalog_collection.catalogs[0], self.hips_deploy._catalog)  # correct catalog chosen
        get_catalog_by_url.assert_called_once_with(HipsDefaultValues.catalog_url.value)  # correct url requested
        get_catalog_by_id.assert_not_called()  # catalog given by url, not id
        _copy_solution_in_catalog.assert_not_called()  # catalog remote -> do not copy
        download_catalog.assert_called_once()  # remote -> download
        _copy_folder_in_local_catalog.assert_not_called()  # remote -> do not copy locally
        _copy_and_zip.assert_called_once_with(Path("myPath"))  # remote -> zip to repo
        _copy_cover_to_repo.assert_called_once_with(Path("myPath"))  # remote -> cover outside zip
        _create_yaml_file_in_repo.assert_called_once_with()  # remote -> create yaml
        _create_hips_merge_request.assert_called_once_with(  # remote -> create MR
            ["copiedYmlFilePath", "solution_zip"] + ["cover1", "cover2"], False, False, None, None
        )

    @patch('hips.core.controller.deploy_manager.load')
    def test_deploy_catalog_not_given(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        _copy_solution_in_catalog = MagicMock(return_value=None)
        self.hips_deploy._copy_folder_in_local_catalog = _copy_solution_in_catalog

        _copy_folder_in_local_catalog = MagicMock(return_value="copiedSolutionFilePath")
        self.hips_deploy._copy_folder_in_local_catalog = _copy_folder_in_local_catalog

        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.hips_deploy._copy_and_zip = _copy_and_zip

        _copy_cover_to_repo = MagicMock(return_value=["cover1", "cover2"])
        self.hips_deploy._copy_cover_to_repo = _copy_cover_to_repo

        _create_yaml_file_in_repo = MagicMock(return_value="copiedYmlFilePath")
        self.hips_deploy._create_yaml_file_in_repo = _create_yaml_file_in_repo

        _create_hips_merge_request = MagicMock(return_value=None)
        self.hips_deploy._create_hips_merge_request = _create_hips_merge_request

        download_catalog = MagicMock(return_value="aRepository")
        self.test_catalog_collection.catalogs[0].download = download_catalog

        get_catalog_by_url = MagicMock(return_value=self.test_catalog_collection.catalogs[0])
        self.test_catalog_collection.get_catalog_by_url = get_catalog_by_url

        get_catalog_by_id = MagicMock(None)
        self.test_catalog_collection.get_catalog_by_id = get_catalog_by_id

        # call
        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy.deploy(deploy_path="myPath",
                                catalog=None,
                                dry_run=False,
                                trigger_pipeline=False)

        # assert
        self.assertEqual(self.test_catalog_collection.catalogs[0], self.hips_deploy._catalog)  # correct catalog chosen
        _copy_solution_in_catalog.assert_not_called()  # remote -> do not copy in catalog
        get_catalog_by_id.assert_not_called()  # catalog not given by id
        get_catalog_by_url.assert_not_called()  # catalog not given by url
        download_catalog.assert_called_once()  # remote -> download
        _copy_folder_in_local_catalog.assert_not_called()  # remote -> do not copy locally
        _copy_and_zip.assert_called_once_with(Path("myPath"))  # remote -> zip to repo
        _copy_cover_to_repo.assert_called_once_with(Path("myPath"))  # remote -> cover outside zip
        _create_yaml_file_in_repo.assert_called_once_with()  # remote -> create yml
        _create_hips_merge_request.assert_called_once_with(  # remote -> create MR
            ["copiedYmlFilePath", "solution_zip"] + ["cover1", "cover2"], False, False, None, None
        )

    def test_retrieve_head_name(self):
        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy._active_hips = self.active_hips

        self.assertEqual("tsg_tsn_tsv", self.hips_deploy.retrieve_head_name())

    @patch('hips.core.controller.deploy_manager.add_files_commit_and_push', return_value=True)
    def test__create_hips_merge_request(self, git_mock):
        self.create_tmp_repo()

        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips

        self.hips_deploy._create_hips_merge_request([self.closed_tmp_file.name], dry_run=True)

        git_mock.assert_called_once_with(self.repo.heads[1], [self.closed_tmp_file.name],
                                         "Adding new/updated tsg_tsn_tsv", True, True, None, None)

    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict')
    def test__create_yaml_file_in_repo(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        self.create_tmp_repo()

        self.hips_deploy._catalog = self.test_catalog_collection.catalogs[1]
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips

        y_path = self.hips_deploy._create_yaml_file_in_repo()

        self.assertEqual(Path(self.repo.working_tree_dir).joinpath("catalog", "tsg", "tsn", "tsv", "tsn.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)

    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict')
    def test__get_cache_suffix(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        # prepare
        self.create_tmp_repo()
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips
        self.hips_deploy._catalog = self.test_catalog_collection.local_catalog

        result = Path(self.repo.working_tree_dir).joinpath(
            HipsDefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv",
            "_".join(["tsg", "tsn", "tsv"]) + ".zip"
        )

        self.assertEqual(result, self.hips_deploy._get_cache_suffix())

    @patch('hips.core.controller.deploy_manager.copy', return_value="absPathCopyOfCover")
    def test__copy_cover_to_repo(self, copy_mock):
        # set covers
        self.active_hips["covers"] = ["example_cover1.png", "example_cover2.png"]

        # prepare fake covers and solution_file
        Path(self.tmp_dir.name).joinpath("example_cover1.png").touch()
        Path(self.tmp_dir.name).joinpath("example_cover2.png").touch()
        Path(self.tmp_dir.name).joinpath(HipsDefaultValues.solution_default_name.value).touch()

        self.create_tmp_repo()
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips
        self.hips_deploy._catalog = self.test_catalog_collection.local_catalog

        tmp_dir = Path(self.tmp_dir.name)
        target_dir = Path(self.repo.working_tree_dir).joinpath(
            HipsDefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv"
        )

        # assert
        self.assertEqual(["absPathCopyOfCover", "absPathCopyOfCover"], self.hips_deploy._copy_cover_to_repo(tmp_dir))

        calls = [call(tmp_dir.joinpath("example_cover1.png"), target_dir.joinpath("example_cover1.png")),
                 call(tmp_dir.joinpath("example_cover2.png"), target_dir.joinpath("example_cover2.png"))]
        copy_mock.assert_has_calls(calls)

    @patch('hips.core.controller.deploy_manager.copy_folder', return_value="absPathCopyFolder")
    @patch('hips.core.controller.deploy_manager.copy', return_value="absPathCopyFile")
    def test__copy_folder_in_local_catalog_file(self, copy_mock, copy_file_mock):
        self.hips_deploy._active_hips = self.active_hips
        self.hips_deploy._catalog = self.test_catalog_collection.local_catalog

        solution_file_to_deploy_locally = Path(self.tmp_dir.name).joinpath("nice_file.py")
        solution_file_to_deploy_locally.touch()

        self.hips_deploy._copy_folder_in_local_catalog(solution_file_to_deploy_locally)

        copy_mock.assert_called_once_with(
            solution_file_to_deploy_locally,
            self.test_catalog_collection.local_catalog.get_solution_cache_path(
                "tsg",
                "tsn",
                "tsv"
            ).joinpath("_".join(["tsg", "tsn", "tsv"]), HipsDefaultValues.solution_default_name.value)
        )
        copy_file_mock.assert_not_called()

    @patch('hips.core.controller.deploy_manager.copy_folder', return_value="absPathCopyFolder")
    @patch('hips.core.controller.deploy_manager.copy', return_value="absPathCopyFile")
    def test__copy_folder_in_local_catalog_folder(self, copy_mock, copy_file_mock):
        self.hips_deploy._active_hips = self.active_hips
        self.hips_deploy._catalog = self.test_catalog_collection.local_catalog

        solution_folder_to_deploy_locally = Path(self.tmp_dir.name)
        solution_folder_to_deploy_locally.joinpath("nice_file.py").touch()
        solution_folder_to_deploy_locally.joinpath("a_nice_cover.png").touch()

        self.hips_deploy._copy_folder_in_local_catalog(solution_folder_to_deploy_locally)

        copy_file_mock.assert_called_once_with(
            solution_folder_to_deploy_locally,
            self.test_catalog_collection.local_catalog.get_solution_cache_path(
                "tsg",
                "tsn",
                "tsv"
            ).joinpath("_".join(["tsg", "tsn", "tsv"])),
            copy_root_folder=False
        )
        copy_mock.assert_not_called()

    @patch('hips.core.controller.deploy_manager.zip_folder', return_value="absPathZipFile")
    @patch('hips.core.controller.deploy_manager.zip_paths', return_value="absPathZipFile")
    def test__copy_and_zip(self, zip_path_mock, zip_folder):
        self.create_tmp_repo()
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips
        self.hips_deploy._catalog = self.test_catalog_collection.local_catalog

        solution_folder_to_deploy_locally = Path(self.tmp_dir.name)
        solution_file_to_deploy_locally = Path(self.tmp_dir.name).joinpath("nice_file.py")
        solution_file_to_deploy_locally.touch()

        # result
        r = Path(self.repo.working_tree_dir).joinpath(
            self.test_catalog_collection.local_catalog.get_solution_cache_zip_suffix("tsg", "tsn", "tsv")
        )

        # copy and zip a folder
        self.hips_deploy._copy_and_zip(solution_folder_to_deploy_locally)
        zip_folder.assert_called_once_with(solution_folder_to_deploy_locally, r)
        zip_path_mock.assert_not_called()

        # reset
        zip_path_mock.reset_mock()
        zip_folder.reset_mock()

        # copy and zip a file
        self.hips_deploy._copy_and_zip(solution_file_to_deploy_locally)
        zip_path_mock.assert_called_once_with([solution_file_to_deploy_locally], r)
        zip_folder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
