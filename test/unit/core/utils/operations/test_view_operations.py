from test.unit.test_unit_core_common import TestUnitCoreCommon

from album.core.utils.operations.view_operations import (
    filter_latest_solutions,
    get_solution_as_string,
)
from album.runner.core.model.solution import Solution


class TestViewOperations(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_filter_latest_solutions(self):
        def solution(group, name, version):
            return {"setup": {"group": group, "name": name, "version": version}}

        index_dict = {
            "catalogs": [
                {
                    "name": "c1",
                    "solutions": [
                        solution("g", "a", "0.2.0"),
                        solution("g", "a", "0.10.0"),
                        solution("g", "a", "0.1.0-SNAPSHOT"),
                        solution("g", "b", "0.1.0-SNAPSHOT"),
                    ],
                },
                {"name": "c2", "solutions": [solution("g", "a", "0.1.0")]},
            ]
        }

        filter_latest_solutions(index_dict)

        # numeric order; a version that is not PEP 440 (SNAPSHOT) ranks below the others
        self.assertEqual(
            [solution("g", "a", "0.10.0"), solution("g", "b", "0.1.0-SNAPSHOT")],
            index_dict["catalogs"][0]["solutions"],
        )
        # each catalog on its own
        self.assertEqual(
            [solution("g", "a", "0.1.0")], index_dict["catalogs"][1]["solutions"]
        )

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
