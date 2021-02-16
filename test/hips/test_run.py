import unittest
import hips.run
import unittest.mock
from unittest.mock import patch

from test.test_hips_common import TestHipsCommon


class TestHipsRun(TestHipsCommon):

    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    @patch('hips.run.get_environment_name', return_value="hips")
    @patch('hips.run._get_environment_dict', return_value={b"hips": b"/some/path"})
    def test_set_environment_path(self, _, __):

        self.some_hips = hips.Hips(self.attrs)

        self.assertTrue("/some/path" == hips.run.get_environment_path(self.some_hips),
                        "get_environment_name returns false value!")

    @unittest.skip("Needs to be implemented!")
    def test_run(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_run_script(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_environment_exists(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_environment(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__get_environment_dict(self):
        # ToDo: implement
        pass


def test_run():
    run_suite = unittest.TestSuite()
    run_suite.addTest(TestHipsRun('test_download_environment_yaml'))
    run_suite.addTest(TestHipsRun('test_get_environment_path'))
    return run_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_run())
