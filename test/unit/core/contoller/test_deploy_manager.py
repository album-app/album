import os
import unittest
from pathlib import Path
from unittest.mock import patch

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

    @unittest.skip("Needs to be implemented!")
    def test_deploy(self):
        pass

    def test_retrieve_head_name(self):
        self.hips_deploy.catalog_configuration = self.config
        self.hips_deploy.active_hips = self.active_hips

        self.assertEqual("tsg_tsn_tsv", self.hips_deploy.retrieve_head_name())

    @patch('hips.core.controller.deploy_manager.add_files_commit_and_push', return_value=True)
    def test__create_hips_merge_request(self, git_mock):
        self.create_tmp_repo()

        self.hips_deploy.catalog_configuration = self.config
        self.hips_deploy.repo = self.repo
        self.hips_deploy.active_hips = self.active_hips

        self.hips_deploy._create_hips_merge_request([self.closed_tmp_file.name], dry_run=True)

        git_mock.assert_called_once_with(self.repo.heads[1], [self.closed_tmp_file.name],
                                         "Adding new/updated tsg_tsn_tsv", True, True)

    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict')
    def test__create_yaml_file_in_repo(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        self.create_tmp_repo()

        self.hips_deploy.catalog_configuration = self.config
        self.hips_deploy.repo = self.repo
        self.hips_deploy.active_hips = self.active_hips

        y_path = self.hips_deploy._create_yaml_file_in_repo()

        self.assertEqual(Path(self.repo.working_tree_dir).joinpath("catalog", "tsg", "tsn", "tsv", "tsn.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)

    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict')
    def test__create_yml_string(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        self.hips_deploy.catalog_configuration = self.config
        self.hips_deploy.active_hips = self.active_hips

        self.assertEqual("group: tsg\nname: tsn\nversion: tsv\n", self.hips_deploy._create_yml_string())

    def test_copy_solution_to_repository(self):
        self.create_tmp_repo()

        self.hips_deploy.catalog_configuration = self.config
        self.hips_deploy.repo = self.repo
        self.hips_deploy.active_hips = self.active_hips

        self.hips_deploy._copy_solution_to_repository(self.closed_tmp_file.name)

        self.assertTrue(os.path.isfile(
            os.path.join(str(self.repo.working_tree_dir), "solutions", "tsg", "tsn", "tsv", "tsn.py")
        ))


if __name__ == '__main__':
    unittest.main()
