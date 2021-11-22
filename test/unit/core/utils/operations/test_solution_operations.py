from io import StringIO
from pathlib import Path
from unittest.mock import patch

from album.core.model.default_values import DefaultValues

from album.core.model.catalog import Catalog

from album.core.model.configuration import Configuration
from album.core.utils.operations.solution_operations import set_cache_paths, get_deploy_dict, get_deploy_keys
from album.runner.model.solution import Solution
from test.unit.test_unit_common import TestUnitCommon


class TestUnitSolutionOperations(TestUnitCommon):
    
    def setUp(self):
        super().setUp()
        Configuration().setup(base_cache_path=Path(self.tmp_dir.name).joinpath("album"))

    def tearDown(self) -> None:
        super().tearDown()

    test_environment_yml = StringIO("""name: unit-test-env
channels:
  - conda-forge
  - defaults
""")

    def test_set_cache_paths(self):
        config = Configuration()

        active_solution = Solution(self.solution_default_dict)

        catalog = Catalog(0, "catalog_name_solution_lives_in", "")
        set_cache_paths(active_solution, catalog)

        self.assertEqual(
            Path(config.cache_path_download).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation.data_path
        )
        self.assertEqual(
            Path(config.cache_path_app).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation.app_path
        )
        self.assertEqual(
            catalog.path.joinpath(
                DefaultValues.cache_path_solution_prefix.value, "tsg", "tsn", "tsv"
            ),
            active_solution.installation.package_path
        )
        self.assertEqual(
            Path(config.cache_path_tmp_internal).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation.internal_cache_path
        )
        self.assertEqual(
            Path(config.cache_path_tmp_user).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation.user_cache_path
        )

    def test_get_deploy_dict(self):
        active_solution = Solution(self.solution_default_dict)
        self.assertEqual(self.solution_default_dict, get_deploy_dict(active_solution))

    def test_get_deploy_dict_additional_values(self):
        # base keys
        attrs_dict_result = {}
        for idx, key in enumerate(get_deploy_keys()):
            attrs_dict_result[key] = str(idx)

        # additional values
        attrs_dict_additional = {
            "this_should_not_appear": "Test"
        }

        # create album attrs dict
        attrs_dict = {**attrs_dict_result, **attrs_dict_additional}
        self.assertEqual(len(attrs_dict), len(attrs_dict_additional) + len(attrs_dict_result))

        active_solution = Solution(attrs_dict)

        self.assertEqual(get_deploy_dict(active_solution), attrs_dict_result)
