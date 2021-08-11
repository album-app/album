import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.model.catalog_index import CatalogIndex
from test.unit.test_unit_common import TestUnitCommon


class TestCatalogIndexNew(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_test_config()
        self.catalog_index = CatalogIndex("test", Path(self.tmp_dir.name).joinpath("test_db_file"))

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

    def fill_tags(self):
        self.assertTrue(self.catalog_index.is_table_empty("tag"))

        tag_id1 = self.catalog_index.insert_tag("myTag1", "manual")
        tag_id2 = self.catalog_index.insert_tag("myTag1", "automatic")
        tag_id3 = self.catalog_index.insert_tag("myTag2", "manual")

        self.assertFalse(self.catalog_index.is_table_empty("tag"))

        return tag_id1, tag_id2, tag_id3

    @patch("album.core.model.catalog_index.CatalogIndex.update_name_version")
    def test_create(self, update_name_version_mock):
        # mock
        path = tempfile.mktemp("test_db", ".db")

        catalog_index = CatalogIndex("test2", path)

        # assert
        self.assertTrue(catalog_index.is_created())
        update_name_version_mock.assert_called_once_with("test2", "0.1.0")

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

    # ### tag ###

    def test_insert_tag(self):
        self.assertTrue(self.catalog_index.is_table_empty("tag"))

        # call
        tag_id1 = self.catalog_index.insert_tag("myTag", "manual")
        tag_id2 = self.catalog_index.insert_tag("myTag", "automatic")
        tag_id3 = self.catalog_index.insert_tag("myTag2", "manual")

        # assert
        self.assertEqual(1, tag_id1)
        self.assertEqual(2, tag_id2)
        self.assertEqual(3, tag_id3)
        self.assertEqual(4, self.catalog_index.next_id("tag"))
        self.assertFalse(self.catalog_index.is_table_empty("tag"))

    def test_insert_tag_twice(self):
        self.assertTrue(self.catalog_index.is_table_empty("tag"))

        tag_id = self.catalog_index.insert_tag("myTag", "manual")
        twice = self.catalog_index.insert_tag("myTag", "manual")

        self.assertEqual(1, tag_id)
        self.assertIsNone(twice)

    def test_get_tag(self):
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        # call
        tag = self.catalog_index.get_tag(2)

        # assert
        self.assertEqual(tag_id2, tag["tag_id"])
        self.assertEqual("myTag1", tag["name"])
        self.assertEqual("automatic", tag["assignment_type"])
        self.assertIsNotNone(tag["hash"])

    def test_get_tags_by_hash(self):
        tag_id = self.catalog_index.next_id("tag")
        self.catalog_index.get_cursor().execute(
            "INSERT INTO tag values (?, ?, ?, ?)",
            (tag_id, "tag_name", "assignment_type", "abcdefghij")
        )

        # call
        tag = self.catalog_index.get_tag_by_hash("abcdefghij")

        # assert
        self.assertEqual(tag_id, tag["tag_id"])

    def test_get_tags_by_name(self):
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        # call
        tags = self.catalog_index.get_tags_by_name("myTag1")

        # assert
        self.assertEqual(2, len(tags))
        self.assertEqual(tag_id1, tags[0]["tag_id"])
        self.assertEqual(tag_id2, tags[1]["tag_id"])

    def test_get_tag_by_name_and_type(self):
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        # call
        tag = self.catalog_index.get_tag_by_name_and_type("myTag1", "automatic")

        # assert
        self.assertEqual(tag_id2, tag["tag_id"])
        self.assertEqual("myTag1", tag["name"])
        self.assertEqual("automatic", tag["assignment_type"])

    def test_remove_tag(self):
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        tag = self.catalog_index.get_tag(tag_id2)
        self.assertEqual("automatic", tag["assignment_type"])

        # call
        self.catalog_index.remove_tag(tag_id2)

        # assert
        tag1 = self.catalog_index.get_tag(tag_id1)
        tag2 = self.catalog_index.get_tag(tag_id2)
        tag3 = self.catalog_index.get_tag(tag_id3)

        self.assertIsNone(tag2)
        # tag 2 and 3 should stay!
        self.assertEqual("myTag1", tag1["name"])
        self.assertEqual("manual", tag1["assignment_type"])
        self.assertEqual("myTag2", tag3["name"])

    def test_remove_tag_by_name(self):
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        tag = self.catalog_index.get_tag(tag_id2)
        self.assertEqual("automatic", tag["assignment_type"])

        # call
        self.catalog_index.remove_tag_by_name("myTag1")

        # assert
        tag1 = self.catalog_index.get_tag(tag_id2)
        tag2 = self.catalog_index.get_tag(tag_id2)
        tag3 = self.catalog_index.get_tag(tag_id3)

        self.assertIsNone(tag1)
        self.assertIsNone(tag2)
        self.assertEqual("myTag2", tag3["name"])

    def test_remove_tag_by_name_and_type(self):
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        # call
        self.catalog_index.remove_tag_by_name_and_type("myTag1", "automatic")

        # assert
        tag2 = self.catalog_index.get_tag(tag_id2)
        self.assertIsNone(tag2)

        tag1 = self.catalog_index.get_tag(tag_id1)
        self.assertEqual("myTag1", tag1["name"])
        self.assertEqual("manual", tag1["assignment_type"])

        tag3 = self.catalog_index.get_tag(tag_id3)
        self.assertEqual("myTag2", tag3["name"])

    # ### solution_tag ###

    def test_insert_solution_tags(self):

        solution_id, _ = self.fill_solution()
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        self.assertTrue(self.catalog_index.is_table_empty("solution_tag"))

        # call
        solution_tag_id1 = self.catalog_index.insert_solution_tag(solution_id, tag_id2)
        solution_tag_id2 = self.catalog_index.insert_solution_tag(solution_id, tag_id3)

        # assert
        self.assertEqual(1, solution_tag_id1)
        self.assertEqual(2, solution_tag_id2)
        self.assertFalse(self.catalog_index.is_table_empty("solution_tag"))
        self.assertEqual(3, self.catalog_index.next_id("solution_tag"))

    def test_insert_solution_tag_twice(self):

        solution_id, _ = self.fill_solution()
        tag_id1 = self.catalog_index.insert_tag("myTag1", "manual")

        self.assertTrue(self.catalog_index.is_table_empty("solution_tag"))

        # call
        solution_tag_id = self.catalog_index.insert_solution_tag(solution_id, tag_id1)
        self.assertIsNotNone(solution_tag_id)

        # call twice
        solution_tag_id_twice = self.catalog_index.insert_solution_tag(solution_id, tag_id1)
        self.assertIsNone(solution_tag_id_twice)

    def test_get_solution_tag_by_hash(self):

        solution_tag_id = self.catalog_index.next_id("solution_tag")
        self.catalog_index.get_cursor().execute(
            "INSERT INTO solution_tag values (?, ?, ?, ?)",
            (solution_tag_id, 1, 1, "abcdefghij")
        )

        # call
        solution_tag = self.catalog_index.get_solution_tag_by_hash("abcdefghij")

        # assert
        self.assertEqual(solution_tag_id, solution_tag["solution_tag_id"])

    def test_get_solution_tag_by_solution_id_and_tag_id(self):
        solution_id, _ = self.fill_solution()
        tag_id1, _, _ = self.fill_tags()

        self.assertTrue(self.catalog_index.is_table_empty("solution_tag"))
        solution_tag_id1 = self.catalog_index.insert_solution_tag(solution_id, tag_id1)
        self.assertFalse(self.catalog_index.is_table_empty("solution_tag"))

        # call
        solution_tag = self.catalog_index.get_solution_tag_by_solution_id_and_tag_id(solution_id, tag_id1)

        # assert
        self.assertEqual(solution_tag_id1, solution_tag["solution_tag_id"])

    def test_get_solution_tags(self):
        solution_id, _ = self.fill_solution()
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        self.assertTrue(self.catalog_index.is_table_empty("solution_tag"))

        solution_tag_id1 = self.catalog_index.insert_solution_tag(solution_id, tag_id2)
        solution_tag_id2 = self.catalog_index.insert_solution_tag(solution_id, tag_id3)

        self.assertFalse(self.catalog_index.is_table_empty("solution_tag"))

        # call
        ids = self.catalog_index.get_solution_tags(solution_id)

        # assert
        self.assertEqual([tag_id2, tag_id3], ids)

    def test_remove_solution_tags(self):
        solution_id1, solution_id2 = self.fill_solution()
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        self.assertTrue(self.catalog_index.is_table_empty("solution_tag"))

        solution_tag_id1 = self.catalog_index.insert_solution_tag(solution_id1, tag_id2)
        solution_tag_id2 = self.catalog_index.insert_solution_tag(solution_id1, tag_id3)
        solution_tag_id3 = self.catalog_index.insert_solution_tag(solution_id2, tag_id1)

        self.assertFalse(self.catalog_index.is_table_empty("solution_tag"))

        # call
        self.catalog_index.remove_solution_tags(solution_id1)

        # assert
        self.assertFalse(self.catalog_index.is_table_empty("solution_tag"))
        self.assertEqual([], self.catalog_index.get_solution_tags(solution_id1))
        self.assertEqual([tag_id1], self.catalog_index.get_solution_tags(solution_id2))

    # ### solution ###

    def test_insert_solution(self):
        self.assertTrue(self.catalog_index.is_table_empty("solution"))

        # call
        solution_id1 = self.catalog_index._insert_solution(self.solution_default_dict)

        solution2_default_dict = self.solution_default_dict.copy()
        solution2_default_dict["group"] = "newGrp"
        solution_id2 = self.catalog_index._insert_solution(solution2_default_dict)

        # assert
        self.assertEqual(1, solution_id1)
        self.assertEqual(2, solution_id2)
        self.assertFalse(self.catalog_index.is_table_empty("solution"))

    def test_get_solution(self):
        solution_id1, _ = self.fill_solution()

        # call
        solution = self.catalog_index.get_solution(solution_id1)

        # assert
        self.assertEqual("tsn", solution["name"])

    def test_get_solution_by_doi(self):
        raise NotImplementedError

    def test_get_solution_by_group_name_version(self):
        solution_id1, _ = self.fill_solution()

        # call
        solution = self.catalog_index.get_solution_by_group_name_version("tsg", "tsn", "tsv")

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

        solution = self.catalog_index.get_solution_by_group_name_version(
            self.solution_default_dict["group"],
            self.solution_default_dict["name"],
            self.solution_default_dict["version"]
        )
        self.assertEqual("d1", solution["description"])

        solution_update_default_dict = self.solution_default_dict.copy()
        solution_update_default_dict["description"] = "aNewD"

        # call
        self.catalog_index._update_solution(solution_update_default_dict)

        # assert
        updated_sol = self.catalog_index.get_solution_by_group_name_version(
            solution_update_default_dict["group"],
            solution_update_default_dict["name"],
            solution_update_default_dict["version"]
        )

        self.assertEqual("aNewD", updated_sol["description"])

    def test_remove_solution(self):
        solution_id1, solution_id2 = self.fill_solution()

        # call
        self.catalog_index.remove_solution(solution_id1)

        # assert
        self.assertIsNotNone(self.catalog_index.get_solution(solution_id2))
        self.assertIsNone(self.catalog_index.get_solution(solution_id1))

    def test_remove_solution_by_group_name_version(self):
        # mocks
        get_solution_by_group_name_version = MagicMock(return_value={"solution_id": 1})
        self.catalog_index.get_solution_by_group_name_version = get_solution_by_group_name_version

        remove_solution = MagicMock(return_value=None)
        self.catalog_index.remove_solution = remove_solution

        # call
        self.catalog_index.remove_solution_by_group_name_version("a", "b", "c")

        # assert
        get_solution_by_group_name_version.assert_called_once_with("a", "b", "c")
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
        get_solution_by_group_name_version = MagicMock(return_value=None)
        self.catalog_index.get_solution_by_group_name_version = get_solution_by_group_name_version

        insert_tag = MagicMock(return_value=None)
        self.catalog_index.insert_tag = insert_tag

        update_solution = MagicMock()
        self.catalog_index._update_solution = update_solution

        insert_solution = MagicMock()
        self.catalog_index._insert_solution = insert_solution

        check_requirements = MagicMock(return_value=["g", "n", "v"])
        self.catalog_index.check_requirements = check_requirements

        attrs = self.solution_default_dict.copy()
        attrs["tags"] = ["niceTag1", "niceTag2"]

        # call
        self.catalog_index.update(attrs)

        # assert
        check_requirements.assert_called_once_with(attrs)
        self.assertEqual(2, insert_tag.call_count)
        get_solution_by_group_name_version.assert_called_once_with("g", "n", "v")
        insert_solution.assert_called_once_with(attrs)
        update_solution.assert_not_called()

    def test_update_solution_exists(self):
        # mocks
        get_solution_by_group_name_version = MagicMock(return_value="aNiceSolution")
        self.catalog_index.get_solution_by_group_name_version = get_solution_by_group_name_version

        insert_tag = MagicMock(return_value=None)
        self.catalog_index.insert_tag = insert_tag

        update_solution = MagicMock()
        self.catalog_index._update_solution = update_solution

        insert_solution = MagicMock()
        self.catalog_index._insert_solution = insert_solution

        check_requirements = MagicMock(return_value=["g", "n", "v"])
        self.catalog_index.check_requirements = check_requirements

        attrs = self.solution_default_dict.copy()
        attrs["tags"] = ["niceTag1", "niceTag2"]

        # call
        self.catalog_index.update(attrs)

        # assert
        check_requirements.assert_called_once_with(attrs)
        self.assertEqual(2, insert_tag.call_count)
        get_solution_by_group_name_version.assert_called_once_with("g", "n", "v")
        update_solution.assert_called_once_with(attrs)
        insert_solution.assert_not_called()

    def test_export(self):
        solution_id1, solution_id2 = self.fill_solution()
        tag_id1, tag_id2, tag_id3 = self.fill_tags()

        solution_tag_id1 = self.catalog_index.insert_solution_tag(solution_id1, tag_id2)
        solution_tag_id2 = self.catalog_index.insert_solution_tag(solution_id1, tag_id3)
        solution_tag_id3 = self.catalog_index.insert_solution_tag(solution_id2, tag_id1)

        # call
        p = Path(self.tmp_dir.name).joinpath("export_index")
        self.catalog_index.export(p)

        # assert
        with open(p) as export_file:
            r = export_file.readlines()

        import_list = json.loads(r[0])

        solution1_import = json.loads(import_list[0])
        self.assertEqual("tsg", solution1_import["group"])
        self.assertEqual([tag_id2, tag_id3], solution1_import["tags"])

        solution2_import = json.loads(import_list[1])
        self.assertEqual("anotherGroup", solution2_import["group"])
        self.assertEqual([tag_id1], solution2_import["tags"])

    def test__len__(self):
        solution_id1, solution_id2 = self.fill_solution()

        self.assertEqual(2, len(self.catalog_index))
