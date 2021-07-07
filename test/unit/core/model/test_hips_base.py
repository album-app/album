from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from hips.core.controller.conda_manager import CondaManager
from hips.core.model.environment import Environment
from hips.core.model.hips_base import HipsClass
from test.unit.test_common import TestHipsCommon


class TestHipsBase(TestHipsCommon):

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

    def test_init_(self):
        hips_dict = {
            "group": "gr1",
            "version": "v1",
            "name": "n1",
            "min_hips_version": "1",
            "dependencies": {'environment_file': self.test_environment_yml}
        }
        tmp_folder = self.tmp_dir.name

        active_hips = HipsClass(hips_dict)

        self.assertEqual(None, active_hips.environment)
        self.assertEqual(None, active_hips.cache_path_download)
        self.assertEqual(None, active_hips.cache_path_app)
        self.assertEqual(None, active_hips.cache_path_solution)

    def test_set_cache_paths(self):
        self.create_test_config()
        config = self.test_catalog_collection.configuration

        active_hips = HipsClass(self.hips_default_dict)

        active_hips.set_cache_paths("catalog_id_hips_lives_in")

        self.assertEqual(
            Path(config.cache_path_download).joinpath(
                "catalog_id_hips_lives_in", "gr1", "n1", "v1"
            ),
            active_hips.cache_path_download
        )
        self.assertEqual(
            Path(config.cache_path_app).joinpath(
                "catalog_id_hips_lives_in", "gr1", "n1", "v1"
            ),
            active_hips.cache_path_app
        )
        self.assertEqual(
            Path(config.cache_path_solution).joinpath(
                "catalog_id_hips_lives_in", "gr1", "n1", "v1"
            ),
            active_hips.cache_path_solution
        )

    @patch('hips.core.model.hips_base.HipsClass.set_cache_paths')
    @patch('hips.core.model.environment.Environment.__init__')
    def test_set_environment(self, environment_init_mock, _):
        # mocks
        environment_init_mock.return_value = None

        active_hips = HipsClass(self.hips_default_dict)

        active_hips.set_environment("catalog_id_hips_lives_in")

        # assert
        environment_init_mock.assert_called_once_with(
            active_hips.dependencies, cache_name="n1", cache_path=None

        )

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
