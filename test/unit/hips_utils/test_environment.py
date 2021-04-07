import os
import tempfile
import unittest.suite
from unittest.mock import patch

from xdg import xdg_cache_home

import hips
import hips.hips_base
from test.unit.test_common import TestHipsCommon
from hips_utils.environment import parse_environment_name_from_yaml, download_environment_yaml, set_environment_name


class TestEnvironment(TestHipsCommon):

    def setUp(self):
        """Setup things necessary for all tests of this class"""
        # self.something_all_tests_use = some_value
        pass

    @patch('hips_utils.environment.download_resource', return_value="test.yml")
    @patch('hips_utils.environment.parse_environment_name_from_yaml', return_value="test")
    @patch('hips_utils.environment.Path.exists')
    def test_set_environment_name(self, _, __, path_exists):

        # hips with no dependency -> hips_full
        hips_no_deps = hips.hips_base.HipsClass(self.attrs)

        # hips with environment_name
        self.attrs = {
            "dependencies": {
                "environment_name": "test_name"
            }
        }

        hips_environment_name = hips.hips_base.HipsClass(self.attrs)

        # hips with environment file
        self.attrs = {
            "dependencies": {
                "environment_file": "test.yaml"
            }
        }
        hips_environment_file = hips.hips_base.HipsClass(self.attrs)

        # hips with environment url
        self.attrs = {
            "dependencies": {
                "environment_file": "fake_url"
            }
        }
        hips_environment_url = hips.hips_base.HipsClass(self.attrs)

        self.assertTrue(set_environment_name(hips_no_deps) == "hips_full",
                        "hips_no_deps: Environment name wrong!")

        self.assertTrue(set_environment_name(hips_environment_name) == "test_name",
                        "hips_environment_name: Environment name wrong!")

        path_exists.return_value = True
        self.assertTrue(set_environment_name(hips_environment_file) == "test",
                        "hips_environment_file: Environment name wrong!")

        path_exists.return_value = False  # ToDo: this is not working properly. Idk why?!?
        self.assertTrue(set_environment_name(hips_environment_url) == "test",
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
        self.assertTrue(parse_environment_name_from_yaml(test_yaml.name) == "test_environment",
                        "Environment name parsing went wrong!")

    @unittest.skip("Needs to be implemented!")
    def test_run_in_environment(self):
        # ToDo: implement
        pass


if __name__ == '__main__':
    unittest.main()
