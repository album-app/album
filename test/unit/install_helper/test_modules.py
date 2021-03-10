import hips.run
import os
import shutil
from xdg import xdg_cache_home
import unittest.mock
from unittest.mock import patch

import install_helper.modules

from test.unit.test_common import TestHipsCommon


class TestInstallHelperModules(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    @patch('install_helper.modules.xdg_data_dirs', return_value=[xdg_cache_home()])
    def test_download_repository(self, _):
        # clean
        shutil.rmtree(xdg_cache_home().joinpath("test"), ignore_errors=True)

        # create hips
        self.attrs = {
            "git_repo": "https://github.com/rmccue/test-repository.git",
            "name": "test"
        }
        hips_with_git_repo = hips.Hips(self.attrs)

        # run
        install_helper.modules.download_hips_repository(hips_with_git_repo)

        # check
        self.assertIn("test", os.listdir(str(xdg_cache_home())), "Download failed!")
        self.assertTrue(os.getcwd() == str(xdg_cache_home().joinpath("test")), "Wrong working directory!")

        # ToDo: finish test writing

        # checkout old version of repo

        # run again
        install_helper.modules.download_hips_repository(hips_with_git_repo)

        # assert that repo has been updated to head!


if __name__ == '__main__':
    unittest.main()
