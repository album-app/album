import os
import unittest

from xdg import xdg_cache_home

from test.unit.test_common import TestGitCommon
from hips.core.model.hips_base import HipsClass
import hips.core.deploy as deploy
from hips.ci.zenodo_api import ZenodoAPI


class TestHipsDeploy(TestGitCommon):
    def setUp(self) -> None:
        self.zenodoAPI = ZenodoAPI('url', 'access_token')

    def test_get_hips_deploy_dict(self):

        # base keys
        attrs_dict_result = {}
        for idx, key in enumerate(deploy.deploy_keys):
            attrs_dict_result[key] = str(idx)

        # additional values
        attrs_dict_additional = {
            "this_should_not_appear": "Test"
        }

        # create hips attrs dict
        attrs_dict = {**attrs_dict_result, **attrs_dict_additional}
        assert len(attrs_dict) == len(attrs_dict_additional) + len(attrs_dict_result)

        active_hips = HipsClass(attrs_dict)

        self.assertEqual(deploy.get_hips_deploy_dict(active_hips), attrs_dict_result)

    def test__create_yaml_in_repo_file(self):

        # create hips
        attrs_dict = {}
        for idx, key in enumerate(deploy.deploy_keys):
            attrs_dict[key] = str(idx)
        attrs_dict["name"] = "test_solution_name"
        active_hips = HipsClass(attrs_dict)

        # paths
        basepath = xdg_cache_home().joinpath("testGitRepo")
        expected_file = basepath.joinpath("catalog", "test_solution_name.yml")

        # create repo
        self.create_tmp_repo()
        os.makedirs(str(basepath.joinpath("catalog")), exist_ok=True)

        deploy._create_yaml_file_in_repo(self.repo, active_hips)
        self.assertTrue(os.path.isfile(str(expected_file)))


if __name__ == '__main__':
    unittest.main()
