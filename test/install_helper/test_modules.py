import unittest
import hips.run
import os
import shutil
from xdg import xdg_cache_home
import unittest.mock
from unittest.mock import patch

import install_helper.modules

from test.test_common import TestHipsCommon


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
        self.git_repo = "https://github.com/rmccue/test-repository.git"
        self.name = "test"
        hips_with_git_repo = hips.Hips(self.attrs)

        # run
        install_helper.modules.download_repository(hips_with_git_repo)

        # check
        self.assertIn("test", os.listdir(str(xdg_cache_home())), "Download failed!")
        self.assertTrue(os.getcwd() == str(xdg_cache_home().joinpath("test")), "Wrong working directory!")

        # ToDo: finish test writing

        # checkout old version of repo

        # run again
        install_helper.modules.download_repository(hips_with_git_repo)

        # assert that repo has been updated to head!


def test_modules_run():
    run_suite = unittest.TestSuite()
    run_suite.addTest(TestInstallHelperModules('test_download_repository'))

    return run_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    result = runner.run(test_modules_run())

    if result.wasSuccessful():
        exit(0)
    else:
        exit(1)
