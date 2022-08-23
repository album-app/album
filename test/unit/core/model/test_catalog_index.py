import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.model.catalog_index import CatalogIndex
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner.core.model.coordinates import Coordinates
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCatalogIndex(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.catalog_index = CatalogIndex(
            "test", Path(self.tmp_dir.name).joinpath("test_db_file")
        )
        self.is_empty_or_full(empty=True)

    def tearDown(self):
        super().tearDown()

    def fill_solution(self):
        self.assertTrue(self.catalog_index.is_table_empty("solution"))

        solution_id1_dict = self.solution_default_dict.copy()
        solution_id1 = self.catalog_index._insert_solution(solution_id1_dict)

        solution_id2_dict = solution_id1_dict.copy()
        solution_id2_dict["group"] = "anotherGroup"
        solution_id2 = self.catalog_index._insert_solution(solution_id2_dict)

        self.assertFalse(self.catalog_index.is_table_empty("solution"))
        self.assertEqual(1, solution_id1)
        self.assertEqual(2, solution_id2)

        return solution_id1, solution_id2

    def is_empty_or_full(self, empty=True):
        c = self.catalog_index.get_cursor()

        r = c.execute("select* from sqlite_master;").fetchall()

        tables = []
        for row in r:
            tables.append(row["tbl_name"])

        for t in tables:
            if t != "catalog_index":  # catalog_index is never empty
                if empty:
                    self.assertTrue(self.catalog_index.is_table_empty(t))
                else:
                    self.assertFalse(self.catalog_index.is_table_empty(t))

        self.catalog_index.close_current_connection()

    @patch("album.core.model.catalog_index.CatalogIndex.update_name_version")
    def test_create(self, update_name_version_mock):
        # mock
        path = tempfile.mktemp("test_db", ".db")

        catalog_index = CatalogIndex("test2", path)

        # assert
        self.assertTrue(catalog_index.is_created())
        update_name_version_mock.assert_called_once_with("test2", "0.1.0", close=False)

    def test_is_empty(self):
        self.assertTrue(self.catalog_index.is_empty())

    def test_is_table_empty(self):
        self.assertTrue(self.catalog_index.is_table_empty("tag"))
        self.assertTrue(self.catalog_index.is_table_empty("solution"))
        self.assertTrue(self.catalog_index.is_table_empty("solution_tag"))

    # ### catalog_index ###

    def test_update_name_version(self):
        # pre-assert
        self.assertEqual("test", self.catalog_index.get_name())

        # call
        self.catalog_index.update_name_version("myName", self.catalog_index.version)

        # assert
        self.assertEqual("myName", self.catalog_index.get_name())

    def test_get_name(self):
        self.assertEqual("test", self.catalog_index.get_name())

    def test_get_version(self):
        self.assertEqual("0.1.0", self.catalog_index.get_version())

    # ### metadata ###
    def test__insert_author(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("author"))

        # call
        self.catalog_index._insert_author("myAuthor")

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("author"))

    def test__insert_tag(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("tag"))

        # call
        self.catalog_index._insert_tag("myTag")

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("tag"))

    def test__insert_citation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("citation"))

        # call
        self.catalog_index._insert_citation({"text": "myCitation", "doi": "abc/def"})

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("citation"))

    def test__insert_argument(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("argument"))

        arg = {
            "name": "myName",
            "type": "myType",
            "description": "myDescription",
            "default": "myDefaultValue",
        }
        # call
        self.catalog_index._insert_argument(arg)

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("argument"))

    def test__insert_custom(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("custom"))

        # call
        self.catalog_index._insert_custom_key("my_key", "my_value")

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("custom"))

    def test__insert_cover(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("cover"))

        # call
        self.catalog_index._insert_cover(
            {"source": "myCover", "description": "myDescription"}, 1
        )

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("cover"))

    def test__insert_documentation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("documentation"))

        # call
        self.catalog_index._insert_documentation("myDocumentation", 1)

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("documentation"))

    def test__exists_author(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("author"))

        # assert
        self.assertIsNone(self.catalog_index._exists_author("myAuthor"))

        r = self.catalog_index._insert_author("myAuthor")

        self.assertEqual(r, self.catalog_index._exists_author("myAuthor"))

    def test__exists_tag(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("tag"))

        # assert
        self.assertIsNone(self.catalog_index._exists_tag("myTag"))

        r = self.catalog_index._insert_tag("myTag")

        self.assertEqual(r, self.catalog_index._exists_tag("myTag"))

    def test__exists_citation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("citation"))

        citation = {"text": "myCitation", "doi": "abc/def"}
        citation_minimal = {"text": "myCitationMin"}

        # assert
        self.assertIsNone(self.catalog_index._exists_citation(citation))
        self.assertIsNone(self.catalog_index._exists_citation(citation_minimal))

        r1 = self.catalog_index._insert_citation(citation)
        r2 = self.catalog_index._insert_citation(citation_minimal)

        self.assertEqual(r1, self.catalog_index._exists_citation(citation))
        self.assertEqual(r2, self.catalog_index._exists_citation(citation_minimal))

    def test__exists_argument(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("argument"))

        arg = {
            "name": "myName",
            "type": "myType",
            "description": "myDescription",
            "default": "myDefaultValue",
        }
        arg_no_type = {
            "name": "myName",
            "description": "myDescription",
            "default": "myDefaultValue",
        }
        arg_no_default = {
            "name": "myName",
            "type": "myType",
            "description": "myDescription",
        }
        arg_minimal = {"name": "myName", "description": "myDescription"}

        # assert
        self.assertIsNone(self.catalog_index._exists_argument(arg))
        self.assertIsNone(self.catalog_index._exists_argument(arg_no_type))
        self.assertIsNone(self.catalog_index._exists_argument(arg_no_default))
        self.assertIsNone(self.catalog_index._exists_argument(arg_minimal))

        r1 = self.catalog_index._insert_argument(arg)
        r2 = self.catalog_index._insert_argument(arg_no_type)
        r3 = self.catalog_index._insert_argument(arg_no_default)
        r4 = self.catalog_index._insert_argument(arg_minimal)

        self.assertEqual(r1, self.catalog_index._exists_argument(arg))
        self.assertEqual(r2, self.catalog_index._exists_argument(arg_no_type))
        self.assertEqual(r3, self.catalog_index._exists_argument(arg_no_default))
        self.assertEqual(r4, self.catalog_index._exists_argument(arg_minimal))

    def test__exists_custom(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("custom"))

        # assert
        self.assertIsNone(self.catalog_index._exists_custom_key("my_key", "my_value"))

        r1 = self.catalog_index._insert_custom_key("my_key", "my_value")

        self.assertEqual(
            r1, self.catalog_index._exists_custom_key("my_key", "my_value")
        )

    def test__exists_cover(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("cover"))

        cover = {"source": "myCover", "description": "myDescription"}

        # assert
        self.assertIsNone(self.catalog_index._exists_cover(cover, 1))

        r = self.catalog_index._insert_cover(cover, 1)

        self.assertEqual(r, self.catalog_index._exists_cover(cover, 1))

    def test__exists_documentation(self):
        self.is_empty_or_full(empty=True)
        self.assertTrue(self.catalog_index.is_table_empty("documentation"))

        # assert
        self.assertIsNone(
            self.catalog_index._exists_documentation("myDocumentation", 1)
        )

        r = self.catalog_index._insert_documentation("myDocumentation", 1)

        self.assertEqual(
            r, self.catalog_index._exists_documentation("myDocumentation", 1)
        )

    # ### solution ###

    def test_insert_solution(self):
        # call
        solution_id1 = self.catalog_index._insert_solution(self.solution_default_dict)

        solution2_default_dict = self.solution_default_dict.copy()
        solution2_default_dict["group"] = "newGrp"
        solution_id2 = self.catalog_index._insert_solution(solution2_default_dict)

        # assert
        self.assertEqual(1, solution_id1)
        self.assertEqual(2, solution_id2)

        self.is_empty_or_full(empty=False)

    def test_get_solution(self):
        solution_id1, _ = self.fill_solution()

        # call
        solution = self.catalog_index.get_solution(solution_id1)

        # assert
        self.assertEqual("tsn", solution["name"])

    def test_get_solution_by_group_name_version(self):
        solution_id1, _ = self.fill_solution()

        # call
        solution = self.catalog_index.get_solution_by_coordinates(
            Coordinates("tsg", "tsn", "tsv")
        )

        # assert
        self.assertEqual(solution_id1, solution["solution_id"])

    def test_get_solution_by_doi(self):
        default_dict = self.solution_default_dict.copy()
        default_dict["doi"] = "testDoi"
        solution_id1 = self.catalog_index._insert_solution(default_dict)

        # call
        solution = self.catalog_index.get_solution_by_doi("testDoi")

        # assert
        self.assertEqual(solution_id1, solution["solution_id"])

    def test__update_solution(self):
        # prepare
        self.assertTrue(self.catalog_index.is_table_empty("solution"))

        self.catalog_index._insert_solution(self.solution_default_dict)

        coordinates = dict_to_coordinates(self.solution_default_dict)

        solution = self.catalog_index.get_solution_by_coordinates(coordinates)
        self.assertEqual("d1", solution["description"])

        solution_update_default_dict = self.solution_default_dict.copy()
        solution_update_default_dict["description"] = "aNewD"

        # call
        self.catalog_index._update_solution(coordinates, solution_update_default_dict)

        # assert
        updated_sol = self.catalog_index.get_solution_by_coordinates(coordinates)

        self.assertEqual("aNewD", updated_sol["description"])

    def test__update_solution_not_exist(self):
        self.assertTrue(self.catalog_index.is_table_empty("solution"))

        coordinates = dict_to_coordinates(self.solution_default_dict)

        with self.assertRaises(RuntimeError):
            self.catalog_index._update_solution(coordinates, self.solution_default_dict)

    def test_remove_solution(self):
        solution_id1, solution_id2 = self.fill_solution()

        # call
        self.catalog_index.remove_solution(solution_id1)

        # assert
        self.assertIsNotNone(self.catalog_index.get_solution(solution_id2))
        self.assertIsNone(self.catalog_index.get_solution(solution_id1))

        self.is_empty_or_full(empty=False)

        # call again
        self.catalog_index.remove_solution(solution_id2)

        self.is_empty_or_full(empty=True)

    def test_remove_solution_by_group_name_version(self):
        # mocks
        get_solution_by_group_name_version = MagicMock(return_value={"solution_id": 1})
        self.catalog_index.get_solution_by_coordinates = (
            get_solution_by_group_name_version
        )

        remove_solution = MagicMock(return_value=None)
        self.catalog_index.remove_solution = remove_solution

        # call
        self.catalog_index.remove_solution_by_group_name_version(
            Coordinates("a", "b", "c")
        )

        # assert
        get_solution_by_group_name_version.assert_called_once_with(
            Coordinates("a", "b", "c"), close=True
        )
        remove_solution.assert_called_once_with(1)

    # ### catalog_features ###

    @unittest.skip("Needs to be implemented!")
    def test_insert(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove(self):
        pass

    def test_update(self):
        # mocks
        get_solution_by_coordinates = MagicMock(return_value=None)
        self.catalog_index.get_solution_by_coordinates = get_solution_by_coordinates

        update_solution = MagicMock()
        self.catalog_index._update_solution = update_solution

        insert_solution = MagicMock()
        self.catalog_index._insert_solution = insert_solution

        attrs = self.solution_default_dict.copy()
        attrs["tags"] = ["niceTag1", "niceTag2"]
        coordinates = Coordinates("g", "n", "v")

        # call
        self.catalog_index.update(coordinates, attrs)

        # assert
        get_solution_by_coordinates.assert_called_once_with(coordinates, close=False)
        insert_solution.assert_called_once_with(attrs, close=True)
        update_solution.assert_not_called()

    def test_update_solution_exists(self):
        # mocks
        get_solution_by_coordinates = MagicMock(return_value="aNiceSolution")
        self.catalog_index.get_solution_by_coordinates = get_solution_by_coordinates

        update_solution = MagicMock()
        self.catalog_index._update_solution = update_solution

        insert_solution = MagicMock()
        self.catalog_index._insert_solution = insert_solution

        attrs = self.solution_default_dict.copy()
        attrs["tags"] = ["niceTag1", "niceTag2"]
        coordinates = Coordinates("g", "n", "v")

        # call
        self.catalog_index.update(coordinates, attrs)

        # assert
        get_solution_by_coordinates.assert_called_once_with(coordinates, close=False)
        update_solution.assert_called_once_with(coordinates, attrs, close=True)
        insert_solution.assert_not_called()

    def test_export(self):
        self.fill_solution()

        # call
        p = Path(self.tmp_dir.name).joinpath("export_index")
        self.catalog_index.export(p)

        # assert
        with open(p) as export_file:
            r = export_file.readlines()

        import_list = json.loads(r[0])

        solution1_import = json.loads(import_list[0])
        self.assertEqual("tsg", solution1_import["group"])

        solution2_import = json.loads(import_list[1])
        self.assertEqual("anotherGroup", solution2_import["group"])

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_keys(self):
        # todo: implement
        pass

    def test__len__(self):
        self.fill_solution()

        self.assertEqual(2, len(self.catalog_index))
