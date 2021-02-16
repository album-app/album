import os
import hips
import tempfile
import unittest.suite
from xdg import xdg_cache_home
from unittest.mock import patch

from test.test_hips_common import TestHipsCommon


class TestHipsInit(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    @patch('hips.set_environment_name', return_value="hips")
    def test_download_environment_yaml(self, _):

        # hips with valid url
        self.dependencies = {
            # ToDo: replace with our environment file once repo is public
            "environment_file": "https://raw.githubusercontent.com/MouseLand/cellpose/master/environment.yml",
        }
        hips_valid_environment_file = hips.Hips(self.attrs)

        # hips with faulty url
        self.dependencies = {
            "environment_file": "faulty_url",
        }
        hips_faulty_environment_file = hips.Hips(self.attrs)

        # case valid url
        r_valid = hips.download_environment_yaml(hips_valid_environment_file)
        self.assertTrue(r_valid == xdg_cache_home().joinpath("environment_file.yml"), "File was not downloaded!")

        # case faulty url
        self.assertRaises(ValueError, hips.download_environment_yaml, hips_faulty_environment_file)

    @patch('hips.download_environment_yaml', return_value="test.yml")
    @patch('hips.parse_environment_name_from_yaml', return_value="test")
    @patch('pathlib.Path.exists')
    def test_set_environment_name(self, _, __, path_exists):

        # hips with no dependency -> hips_full
        hips_no_deps = hips.Hips(self.attrs)

        # hips with environment_name
        self.dependencies = {
            "environment_name": "test_name"
        }
        hips_environment_name = hips.Hips(self.attrs)

        # hips with environment file
        self.dependencies = {
            "environment_file": "test.yaml"
        }
        hips_environment_file = hips.Hips(self.attrs)

        # hips with environment url
        self.dependencies = {
            "environment_file": "fake_url"
        }
        hips_environment_url = hips.Hips(self.attrs)

        self.assertTrue(hips.set_environment_name(hips_no_deps) == "hips_full",
                        "hips_no_deps: Environment name wrong!")

        self.assertTrue(hips.set_environment_name(hips_environment_name) == "test_name",
                        "hips_environment_name: Environment name wrong!")

        path_exists.return_value = True
        self.assertTrue(hips.set_environment_name(hips_environment_file) == "test",
                        "hips_environment_file: Environment name wrong!")

        path_exists.return_value = False  # ToDo: this is not working properly. Idk why?!?
        self.assertTrue(hips.set_environment_name(hips_environment_url) == "test",
                        "hips_environment_url: Environment name wrong!")

    def test_parse_environment_name_from_yaml(self):
        test_yaml = tempfile.NamedTemporaryFile(mode='w+')
        test_yaml.write("""
name: test_environment
dependencies:
    - test_dependency
""")
        test_yaml.flush()
        os.fsync(test_yaml)
        self.assertTrue(hips.parse_environment_name_from_yaml(test_yaml.name) == "test_environment",
                        "Environment name parsing went wrong!")

    @unittest.skip("Needs to be implemented!")
    def test_run_in_environment(self):
        # ToDo: implement
        pass


def test_run():
    run_suite = unittest.TestSuite()
    run_suite.addTest(TestHipsInit('test_download_environment_yaml'))
    run_suite.addTest(TestHipsInit('test_set_environment_name'))
    run_suite.addTest(TestHipsInit('test_parse_environment_name_from_yaml'))

    return run_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(test_run())
