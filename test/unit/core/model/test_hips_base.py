import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from hips.core.controller.conda_manager import CondaManager
from hips.core.model.hips_base import HipsClass


class TestHipsBase(unittest.TestCase):

    def tearDown(self) -> None:
        CondaManager().remove_environment("unit-test-env")

    test_environment_yml = StringIO("""name: unit-test-env
channels:
  - conda-forge
  - defaults
""")

    hips_default_dict = {
        'group': "gr1",
        'name': "n1",
        'description': "d1",
        'version': "v1",
        'format_version': "f1",
        'tested_hips_version': "t1",
        'min_hips_version': "mhv1",
        'license': "l1",
        'git_repo': "g1",
        'authors': "a1",
        'cite': "c1",
        'tags': "t1",
        'documentation': "do1",
        'covers': "co1",
        'sample_inputs': "si1",
        'sample_outputs': "so1",
        'args': [{"action": None}],
        'title': "t1",
    }

    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict')
    @patch('hips.core.model.configuration.HipsConfiguration.get_cache_path_hips')
    def test_init_(self, cache_path_mock, depl_dict_mock):
        hips_dict = {
            "group": "gr1",
            "version": "v1",
            "name": "n1",
            "min_hips_version": "1",
            "dependencies": {'environment_file': self.test_environment_yml}
        }
        tmp_folder = tempfile.gettempdir()

        cache_path_mock.return_value = Path(tmp_folder)
        depl_dict_mock.return_value = hips_dict

        active_hips = HipsClass(hips_dict)

        self.assertEqual("unit-test-env", active_hips.environment.name)
        self.assertEqual(active_hips.environment.yaml_file, Path(tmp_folder).joinpath("n1.yml"))

    def test_get_hips_deploy_dict(self):
        active_hips = HipsClass(self.hips_default_dict)

        self.hips_default_dict["args"][0].pop("action")

        self.assertEqual(self.hips_default_dict, active_hips.get_hips_deploy_dict())

    def test_get_hips_deploy_dict_additional_values(self):

        # base keys
        attrs_dict_result = {}
        for idx, key in enumerate(HipsClass.deploy_keys):
            attrs_dict_result[key] = str(idx)

        # additional values
        attrs_dict_additional = {
            "this_should_not_appear": "Test"
        }

        # create hips attrs dict
        attrs_dict = {**attrs_dict_result, **attrs_dict_additional}
        self.assertEqual(len(attrs_dict), len(attrs_dict_additional) + len(attrs_dict_result))

        active_hips = HipsClass(attrs_dict)

        self.assertEqual(active_hips.get_hips_deploy_dict(), attrs_dict_result)
