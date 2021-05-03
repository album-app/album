import os
import unittest

from xdg import xdg_cache_home

import hips.core.deploy as deploy
from hips.ci.zenodo_api import ZenodoAPI
from hips.core.model.hips_base import HipsClass
from test.unit.test_common import TestGitCommon


class TestHipsDeploy(TestGitCommon):
    def setUp(self) -> None:
        self.zenodoAPI = ZenodoAPI('url', 'access_token')

    def test__create_yaml_in_repo_file(self):

        # create hips
        attrs_dict = {}
        for idx, key in enumerate(HipsClass.deploy_keys):
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
