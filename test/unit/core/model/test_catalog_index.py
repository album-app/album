import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.model.catalog_index import CatalogIndex
from album.core.model.group_name_version import GroupNameVersion
from album.core.utils.operations.resolve_operations import dict_to_group_name_version
from test.unit.test_unit_common import TestUnitCommon


class TestCatalogIndex(TestUnitCommon):

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
        solution = self.catalog_index.get_solution_by_group_name_version(GroupNameVersion("tsg", "tsn", "tsv"))

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
            dict_to_group_name_version(self.solution_default_dict)
        )
        self.assertEqual("d1", solution["description"])

        solution_update_default_dict = self.solution_default_dict.copy()
        solution_update_default_dict["description"] = "aNewD"

        # call
        self.catalog_index._update_solution(solution_update_default_dict)

        # assert
        updated_sol = self.catalog_index.get_solution_by_group_name_version(
            dict_to_group_name_version(solution_update_default_dict)
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
        self.catalog_index.remove_solution_by_group_name_version(GroupNameVersion("a", "b", "c"))

        # assert
        get_solution_by_group_name_version.assert_called_once_with(GroupNameVersion("a", "b", "c"))
        remove_solution.assert_called_once_with(1)

    # ### catalog_features ###

    @unittest.skip("Needs to be implemented!")
    def test_insert(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove(self):
        pass

    @patch("album.core.model.catalog_index.dict_to_group_name_version", return_value=GroupNameVersion("g", "n", "v"))
    def test_update(self, as_group_name_version):
        # mocks
        get_solution_by_group_name_version = MagicMock(return_value=None)
        self.catalog_index.get_solution_by_group_name_version = get_solution_by_group_name_version

        update_solution = MagicMock()
        self.catalog_index._update_solution = update_solution

        insert_solution = MagicMock()
        self.catalog_index._insert_solution = insert_solution

        attrs = self.solution_default_dict.copy()
        attrs["tags"] = ["niceTag1", "niceTag2"]

        # call
        self.catalog_index.update(attrs)

        # assert
        as_group_name_version.assert_called_once_with(attrs)
        get_solution_by_group_name_version.assert_called_once_with(as_group_name_version.return_value)
        insert_solution.assert_called_once_with(attrs)
        update_solution.assert_not_called()

    @patch("album.core.model.catalog_index.dict_to_group_name_version", return_value=GroupNameVersion("g", "n", "v"))
    def test_update_solution_exists(self, as_group_name_version):
        # mocks
        get_solution_by_group_name_version = MagicMock(return_value="aNiceSolution")
        self.catalog_index.get_solution_by_group_name_version = get_solution_by_group_name_version

        update_solution = MagicMock()
        self.catalog_index._update_solution = update_solution

        insert_solution = MagicMock()
        self.catalog_index._insert_solution = insert_solution

        attrs = self.solution_default_dict.copy()
        attrs["tags"] = ["niceTag1", "niceTag2"]

        # call
        self.catalog_index.update(attrs)

        # assert
        as_group_name_version.assert_called_once_with(attrs)
        get_solution_by_group_name_version.assert_called_once_with(as_group_name_version.return_value)
        update_solution.assert_called_once_with(attrs)
        insert_solution.assert_not_called()

    def test_export(self):
        solution_id1, solution_id2 = self.fill_solution()

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

    def test__len__(self):
        solution_id1, solution_id2 = self.fill_solution()

        self.assertEqual(2, len(self.catalog_index))
