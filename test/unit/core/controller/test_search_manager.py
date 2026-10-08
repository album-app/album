import unittest.mock
from argparse import Namespace
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock

from album.core.controller.search_manager import SearchManager
from album.core.utils.operations.view_operations import get_search_result_as_string


class TestSearchManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()

    @staticmethod
    def _search(solutions, keywords, catalog_name="my-catalog"):
        """Run SearchManager.search over an index holding the given setup dicts."""
        entries = []
        for setup in solutions:
            entry = MagicMock()
            entry.setup.return_value = setup
            entry.internal.return_value = {"catalog_id": 1}
            entries.append(entry)
        album = MagicMock()
        index = album.collection_manager.return_value.get_collection_index.return_value
        index.get_all_solutions.return_value = entries
        album.catalogs.return_value.get_by_id.return_value.name.return_value = (
            catalog_name
        )
        return SearchManager(album).search(keywords)

    def test_search(self):
        solutions = [
            {
                "group": "grp",
                "name": "threshold",
                "version": "0.1.0",
                "description": "blur, then threshold",
                "tags": ["binary"],
            },
            {
                "group": "grp",
                "name": "blur",
                "version": "0.1.0",
                "description": "gaussian blur",
                "tags": ["filter", "blur"],
                "args": [{"name": "sigma", "description": "blur radius"}],
                "timestamp": None,
            },
        ]

        # every string field containing the keyword adds one point,
        # results are ordered by score, highest first
        self.assertEqual(
            [("my-catalog:grp:blur:0.1.0", 4), ("my-catalog:grp:threshold:0.1.0", 1)],
            self._search(solutions, ["blur"]),
        )

        # scores of several keywords add up
        self.assertEqual(
            [("my-catalog:grp:threshold:0.1.0", 2), ("my-catalog:grp:blur:0.1.0", 1)],
            self._search(solutions, ["threshold", "radius"]),
        )

        self.assertEqual([], self._search(solutions, ["segmentation"]))

    def test_search_keyword_is_case_insensitive(self):
        solutions = [
            {
                "group": "grp",
                "name": "segmentation-unet",
                "version": "0.1.0",
                "description": "nuclei segmentation",
            }
        ]

        for keyword in ["segmentation", "Segmentation", "SEGMENTATION", "sEgMeNt"]:
            self.assertEqual(
                [("my-catalog:grp:segmentation-unet:0.1.0", 2)],
                self._search(solutions, [keyword]),
                keyword,
            )

    def test_search_field_is_case_insensitive(self):
        solutions = [
            {
                "group": "Imaging",
                "name": "UNet",
                "version": "0.1.0-SNAPSHOT",
                "title": "Cell Segmentation with UNet",
                "tags": ["Segmentation", "DEEP-LEARNING"],
            }
        ]

        # the solution ID keeps the original case of catalog, group and name
        self.assertEqual(
            [("My-Catalog:Imaging:UNet:0.1.0-SNAPSHOT", 2)],
            self._search(solutions, ["segmentation"], catalog_name="My-Catalog"),
        )
        self.assertEqual(
            [("My-Catalog:Imaging:UNet:0.1.0-SNAPSHOT", 3)],
            self._search(
                solutions, ["unet", "deep-learning"], catalog_name="My-Catalog"
            ),
        )

    def test_search_casefolds_non_ascii(self):
        # casefold(), not lower(): lower() turns a capital sigma at the end of
        # a word into "ς" but a lone one into "σ", which would lose the
        # "Σ" match that the plain case-sensitive substring test finds,
        # and lower() does not fold "ß" to "ss"
        solutions = [
            {
                "group": "grp",
                "name": "odos",
                "version": "0.1.0",
                "description": "ΟΔΟΣ Straße",
            }
        ]

        for keyword in ["Σ", "σ", "STRASSE", "straße"]:
            self.assertEqual(
                [("my-catalog:grp:odos:0.1.0", 1)],
                self._search(solutions, [keyword]),
                keyword,
            )

    def test_search_result_as_string(self):
        solutions = [
            {"group": "grp", "name": "Segmentation", "version": "0.1.0"},
            {"group": "grp", "name": "blur", "version": "0.1.0"},
        ]
        args = Namespace(keywords=["SEGMENTATION"])

        res = get_search_result_as_string(args, self._search(solutions, args.keywords))

        self.assertEqual(
            'Search results for "SEGMENTATION" - run `album info SOLUTION_ID` '
            "for more information:\n"
            "[SCORE] SOLUTION_ID\n"
            "[1] my-catalog:grp:Segmentation:0.1.0\n",
            res,
        )


if __name__ == "__main__":
    unittest.main()
