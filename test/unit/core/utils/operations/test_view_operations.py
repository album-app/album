from test.unit.test_unit_core_common import TestUnitCoreCommon

from album.runner.core.model.solution import Solution

from album.core.utils.operations.view_operations import get_solution_as_string


class TestViewOperations(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_get_solution_as_string(self):
        solution_dict = self.solution_default_dict.copy()
        solution_dict["args"] = [
            {
                "name": "a1",
                "type": "string",
                "description": "myDesc",
                "required": True,
                "default": "myDef",
            }
        ]
        solution = Solution(solution_dict)

        # call
        res = get_solution_as_string(solution, "myPath")

        # assert
        self.assertIn("Solution details about myPath:", res)
        self.assertIn("Run parameters:", res)
        self.assertIn(
            "  --a1: (required: True) myDesc (type: string) (default: myDef)\n",
            res,
        )

    def test_get_solution_as_string_argument_without_description(self):
        solution_dict = self.solution_default_dict.copy()
        solution_dict["args"] = [{"name": "a1"}]
        solution = Solution(solution_dict)

        # call
        res = get_solution_as_string(solution, "myPath")

        # assert
        self.assertIn("Run parameters:", res)
        self.assertIn("  --a1:\n", res)
