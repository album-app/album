from io import StringIO

from album.core.model.catalog_index import CatalogIndex
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner.model.solution import Solution
from test.unit.test_unit_common import TestUnitCommon


class TestSolutionOperations(TestUnitCommon):
    
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    test_environment_yml = StringIO("""name: unit-test-env
channels:
  - conda-forge
  - defaults
""")

    def test_get_deploy_dict(self):
        active_solution = Solution(self.solution_default_dict)
        self.assertEqual(self.solution_default_dict, get_deploy_dict(active_solution))

    def test_get_deploy_dict_additional_values(self):
        # base keys
        attrs_dict_result = {}
        for idx, key in enumerate(CatalogIndex.get_solution_column_keys()):
            attrs_dict_result[key] = str(idx)

        # additional values
        attrs_dict_additional = {
            "this_should_not_appear": lambda value: print(value)
        }

        # create album attrs dict
        attrs_dict = {**attrs_dict_result, **attrs_dict_additional}
        self.assertEqual(len(attrs_dict), len(attrs_dict_additional) + len(attrs_dict_result))

        active_solution = Solution(attrs_dict)

        self.assertEqual(get_deploy_dict(active_solution), attrs_dict_result)
