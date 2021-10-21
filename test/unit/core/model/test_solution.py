from io import StringIO
from pathlib import Path
from unittest.mock import patch

from album.core.model.configuration import Configuration
from album.core.model.solution import Solution
from test.unit.test_unit_common import TestUnitCommon


class TestUnitSolution(TestUnitCommon):
    
    def setUp(self):
        super().setUp()
        Configuration().setup(base_cache_path=Path(self.tmp_dir.name).joinpath("album"), configuration_file_path=self.tmp_dir.name)

    def tearDown(self) -> None:
        super().tearDown()

    test_environment_yml = StringIO("""name: unit-test-env
channels:
  - conda-forge
  - defaults
""")

    def test_init_(self):
        solution_dict = {
            "group": "gr1",
            "version": "v1",
            "name": "n1",
            "min_album_version": "1",
            "dependencies": {'environment_file': self.test_environment_yml}
        }
        active_solution = Solution(solution_dict)

        self.assertEqual(None, active_solution.environment)
        self.assertEqual(None, active_solution.data_path)
        self.assertEqual(None, active_solution.app_path)
        self.assertEqual(None, active_solution.package_path)
        self.assertEqual(None, active_solution.cache_path)

    def test_set_cache_paths(self):
        config = Configuration()

        active_solution = Solution(self.solution_default_dict)

        active_solution.set_cache_paths("catalog_name_solution_lives_in")

        self.assertEqual(
            Path(config.cache_path_download).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.data_path
        )
        self.assertEqual(
            Path(config.cache_path_app).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.app_path
        )
        self.assertEqual(
            Path(config.cache_path_solution).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.package_path
        )
        self.assertEqual(
            Path(config.cache_path_tmp).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.cache_path
        )

    @patch('album.core.model.solution.Solution.set_cache_paths')
    @patch('album.core.model.environment.Environment.__init__')
    def test_set_environment(self, environment_init_mock, _):
        # mocks
        environment_init_mock.return_value = None

        active_solution = Solution(self.solution_default_dict)

        active_solution.set_environment("catalog_name_solution_lives_in")

        # assert
        environment_init_mock.assert_called_once_with(
            active_solution.dependencies,
            environment_name="catalog_name_solution_lives_in_tsg_tsn_tsv",
            cache_path=active_solution.package_path
        )

    def test_get_deploy_dict(self):
        active_solution = Solution(self.solution_default_dict)
        self.assertEqual(self.solution_default_dict, active_solution.get_deploy_dict())

    def test_get_deploy_dict_additional_values(self):
        # base keys
        attrs_dict_result = {}
        for idx, key in enumerate(Solution.deploy_keys):
            attrs_dict_result[key] = str(idx)

        # additional values
        attrs_dict_additional = {
            "this_should_not_appear": "Test"
        }

        # create album attrs dict
        attrs_dict = {**attrs_dict_result, **attrs_dict_additional}
        self.assertEqual(len(attrs_dict), len(attrs_dict_additional) + len(attrs_dict_result))

        active_solution = Solution(attrs_dict)

        self.assertEqual(active_solution.get_deploy_dict(), attrs_dict_result)
