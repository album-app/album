import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

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
        self.hips_deploy._copy_solution_in_catalog = _copy_solution_in_catalog

        _copy_solution_to_repository = MagicMock(return_value="copiedSolutionFilePath")
        self.hips_deploy._copy_solution_to_repository = _copy_solution_to_repository

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
        self.hips_deploy.deploy(path=None,
                                catalog=os.path.basename(self.tmp_dir.name),
                                dry_run=False,
                                trigger_pipeline=False)

        # assert
        self.assertEqual(self.test_catalog_collection.catalogs[1], self.hips_deploy._catalog)            # correct catalog chosen
        get_catalog_by_id.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_catalog_by_url.assert_not_called()                                          # catalog given by id not url
        _copy_solution_in_catalog.assert_called_once()                                  # local catalog -> copy solution
        _copy_solution_to_repository.assert_not_called()                                # local -> no repo
        _create_yaml_file_in_repo.assert_not_called()                                   # local -> no yaml
        _create_hips_merge_request.assert_not_called()                                  # local -> no merge request
        download_catalog.assert_not_called()                                            # local -> no download

    @patch('hips.core.controller.deploy_manager.load')
    def test_deploy_catalog_in_active_hips(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        _copy_solution_in_catalog = MagicMock(return_value=None)
        self.hips_deploy._copy_solution_in_catalog = _copy_solution_in_catalog

        _copy_solution_to_repository = MagicMock(return_value="copiedSolutionFilePath")
        self.hips_deploy._copy_solution_to_repository = _copy_solution_to_repository

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
        self.hips_deploy.deploy(path="myPath",
                                catalog=None,
                                dry_run=False,
                                trigger_pipeline=False)

        # assert
        self.assertEqual(self.test_catalog_collection.catalogs[0], self.hips_deploy._catalog)             # correct catalog chosen
        get_catalog_by_url.assert_called_once_with(HipsDefaultValues.catalog_url.value)  # correct url requested
        get_catalog_by_id.assert_not_called()                                            # catalog given by url, not id
        _copy_solution_in_catalog.assert_not_called()                                    # catalog remote -> do not copy
        download_catalog.assert_called_once()                                            # remote -> download
        _copy_solution_to_repository.assert_called_once_with("myPath")                   # remote -> copy to cat repo
        _create_yaml_file_in_repo.assert_called_once_with()                              # remote -> create yaml
        _create_hips_merge_request.assert_called_once_with(                              # remote -> create MR
            ["copiedYmlFilePath", "copiedSolutionFilePath"], False, False, None, None
        )

    @patch('hips.core.controller.deploy_manager.load')
    def test_deploy_catalog_not_given(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        _copy_solution_in_catalog = MagicMock(return_value=None)
        self.hips_deploy._copy_solution_in_catalog = _copy_solution_in_catalog

        _copy_solution_to_repository = MagicMock(return_value="copiedSolutionFilePath")
        self.hips_deploy._copy_solution_to_repository = _copy_solution_to_repository

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
        self.hips_deploy.deploy(path="myPath",
                                catalog=None,
                                dry_run=False,
                                trigger_pipeline=False)

        # assert
        self.assertEqual(self.test_catalog_collection.catalogs[0], self.hips_deploy._catalog)     # correct catalog chosen
        _copy_solution_in_catalog.assert_not_called()                            # remote -> do not copy in catalog
        get_catalog_by_id.assert_not_called()                                    # catalog not given by id
        get_catalog_by_url.assert_not_called()                                   # catalog not given by url
        download_catalog.assert_called_once()                                    # remote -> download
        _copy_solution_to_repository.assert_called_once_with("myPath")           # remote -> copy to repo
        _create_yaml_file_in_repo.assert_called_once_with()                      # remote -> create yml
        _create_hips_merge_request.assert_called_once_with(                      # remote -> create MR
            ["copiedYmlFilePath", "copiedSolutionFilePath"], False, False, None, None
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

        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips

        y_path = self.hips_deploy._create_yaml_file_in_repo()

        self.assertEqual(Path(self.repo.working_tree_dir).joinpath("catalog", "tsg", "tsn", "tsv", "tsn.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)

    def test_copy_solution_to_repository(self):
        self.create_tmp_repo()

        self.hips_deploy.catalog_collection = self.test_catalog_collection
        self.hips_deploy._repo = self.repo
        self.hips_deploy._active_hips = self.active_hips
        self.hips_deploy._catalog = self.test_catalog_collection.catalogs[1]

        self.hips_deploy._copy_solution_to_repository(self.closed_tmp_file.name)

        self.assertTrue(os.path.isfile(
            os.path.join(str(self.repo.working_tree_dir), "solutions", "tsg", "tsn", "tsv", "tsn.py")
        ))


if __name__ == '__main__':
    unittest.main()
