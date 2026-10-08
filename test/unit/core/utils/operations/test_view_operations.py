from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock

from album.core.api.model.catalog_updates import ChangeType
from album.core.model.catalog_updates import CatalogUpdates, SolutionChange
from album.core.utils.operations.view_operations import (
    filter_latest_solutions,
    get_index_as_string,
    get_solution_as_string,
    get_updates_as_string,
)
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution

# More entries than CPython caches small ints for (-5..256): from index 257 on, the
# enumerate() counter and len(...) - 1 are equal but no longer the same object.
MANY = 300


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

    def test_get_updates_as_string_marks_last_of_many_solution_changes(self):
        catalog = MagicMock()
        catalog.name.return_value = "cat"
        changes = [
            SolutionChange(
                Coordinates("grp", "name%s" % i, "0.1.0"), ChangeType.CHANGED, "log"
            )
            for i in range(MANY)
        ]

        # call
        res = get_updates_as_string(
            {"cat": CatalogUpdates(catalog, solution_changes=changes)}
        )

        # assert
        self.assertEqual(1, res.count("└─"))
        self.assertEqual(MANY - 1, res.count("├─"))
        self.assertIn("  └─ [CHANGED] grp:name%s:0.1.0\n" % (MANY - 1), res)

    def test_get_index_as_string_marks_last_of_many_solutions(self):
        solutions = [
            {
                "setup": {"group": "grp", "name": "name%s" % i, "version": "0.1.0"},
                "internal": {"installed": False},
            }
            for i in range(MANY)
        ]
        index_dict = {
            "base": "myBase",
            "catalogs": [
                {
                    "name": "cat",
                    "src": "mySrc",
                    "catalog_id": 1,
                    "deletable": True,
                    "solutions": solutions,
                }
            ],
        }

        # call
        res = get_index_as_string(index_dict)

        # assert
        self.assertEqual(1, res.count("   └─ ["))
        self.assertEqual(MANY - 1, res.count("   ├─ ["))
        self.assertIn("   └─ [ ] grp:name%s:0.1.0\n" % (MANY - 1), res)
