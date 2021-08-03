import json
import unittest.mock
from pathlib import Path
from unittest.mock import patch

from anytree import Node

from album.core.model.catalog import CatalogIndex
from album.core.model.default_values import DefaultValues
from test.unit.core.model.test_catalog import sample_index, empty_index
from test.unit.test_unit_common import TestUnitCommon


class TestCatalogIndex(TestUnitCommon):
    def setUp(self):
        super().setUp()
        # fill index file
        cs_file = Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_index_file_name.value)
        with open(cs_file, "w+") as f:
            f.write(sample_index)
        self.cs_file = cs_file

        # fill empty_index file
        self.cs_file_index_empty = Path(self.tmp_dir.name).joinpath("empty_index_file")
        with open(self.cs_file_index_empty, "w+") as f:
            f.write(empty_index)

        # fill emtpy_file
        self.cs_file_empty = Path(self.tmp_dir.name).joinpath("empty_file")
        self.cs_file_empty.touch()

        self.cs_index = CatalogIndex("test", self.cs_file)

    def tearDown(self) -> None:
        super().tearDown()

    def test__init__(self):
        self.assertEqual(1, len(self.cs_index))

    def test__init__index_given(self):
        cs_index = CatalogIndex("test", self.cs_file, index=Node("IndexGiven", **{"version": "0.1.0"}))

        self.assertEqual(0, len(cs_index))

    def test__len__(self):
        self.assertEqual(1, len(self.cs_index))

        attrs = {
            "group": "group0",
            "name": "name0",
            "version": "version0"
        }

        self.cs_index.update(node_attrs=attrs)

        self.assertEqual(2, len(self.cs_index))

    def test_load(self):
        self.assertEqual(1, len(self.cs_index))
        self.cs_index.load(self.cs_file_index_empty)
        self.assertEqual(0, len(self.cs_index))

    def test_load_empty_file(self):
        self.assertEqual(1, len(self.cs_index))
        self.cs_index.load(self.cs_file_empty)
        self.assertEqual(1, len(self.cs_index))

    def test_update(self):
        node_attrs = {"name": "myname", "group": "mygroup", "version": "myversion"}

        self.cs_index.load(self.cs_file_index_empty)
        self.assertEqual(len(self.cs_index), 0)
        self.cs_index.update(node_attrs)
        self.assertEqual(len(self.cs_index), 1)

        self.assertIsNotNone(self.cs_index._find_node_by_name_version_and_group(
            self.cs_index.index, "myname", "myversion", "mygroup")
        )

    def test_update_overwrite_old(self):
        res = self.cs_index._find_node_by_name_version_and_group(
            self.cs_index.index, "testName", "testVersion", "testGroup"
        )
        self.assertIsNotNone(res)
        self.assertFalse(hasattr(res, "newAttr"))
        self.assertEqual(1, len(self.cs_index))

        # updated version
        node_attrs = {"name": "testName", "group": "testGroup", "version": "testVersion", "newAttr": "newAttrVal"}
        self.cs_index.update(node_attrs)

        # check changes
        self.assertEqual(1, len(self.cs_index))
        res = self.cs_index._find_node_by_name_version_and_group(
            self.cs_index.index, "testName", "testVersion", "testGroup"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.newAttr, "newAttrVal")

    def test_update_add_version(self):
        res = self.cs_index._find_node_by_name_version_and_group(
            self.cs_index.index, "testName", "testVersion", "testGroup"
        )
        self.assertIsNotNone(res)
        self.assertEqual(1, len(self.cs_index))

        # updated version
        node_attrs = {"name": "testName", "group": "testGroup", "version": "testVersion2"}
        self.cs_index.update(node_attrs)

        # check
        self.assertEqual(2, len(self.cs_index))
        self.assertIsNotNone(self.cs_index._find_node_by_name_version_and_group(
            self.cs_index.index, "testName", "testVersion", "testGroup"
        ))
        self.assertIsNotNone(self.cs_index._find_node_by_name_version_and_group(
            self.cs_index.index, "testName", "testVersion2", "testGroup"
        ))

    def test_save(self):
        self.assertTrue(self.cs_file_empty.stat().st_size == 0)
        self.cs_index.save(self.cs_file_empty)
        self.assertTrue(self.cs_file_empty.stat().st_size > 0)

        self.cs_index.load(self.cs_file_empty)
        self.assertEqual(1, len(self.cs_index))

    def test_get_leaves_dict_list(self):
        l_dict_list = self.cs_index.get_leaves_dict_list()
        self.assertEqual(len(l_dict_list), 1)

    def test_resolve_by_name_version_and_group(self):
        self.assertIsNotNone(
            self.cs_index.resolve_by_name_version_and_group("testName", "testVersion", "testGroup")
        )

    def test_resolve_by_name_version_and_group_no_leaf(self):
        r = self.cs_index.resolve_by_name_version_and_group("testName", "testVersion", "testGroup")
        self.assertIsNotNone(r)
        Node("wrongNode", parent=r)  # resolving not a leaf any more
        with self.assertRaises(RuntimeError):
            self.cs_index.resolve_by_name_version_and_group("testName", "testVersion", "testGroup")

    def test_resolve_by_doi(self):
        self.assertIsNotNone(
            self.cs_index.resolve_by_doi("doi0")
        )

    def test_test_resolve_by_doi_no_leaf(self):
        r = self.cs_index.resolve_by_doi("doi0")
        self.assertIsNotNone(r)
        Node("wrongNode", parent=r)  # resolving not a leaf any more

        with self.assertRaises(RuntimeError) as context:
            self.cs_index.resolve_by_doi("doi0")
            self.assertIn("Ambiguous results", str(context.exception))

    @patch('album.core.model.catalog.CatalogIndex._find_all_nodes_by_attribute')
    def test_test_resolve_by_doi_two_doi(self, fanba_mock):
        fanba_mock.side_effect = [[Node("new1"), Node("new2")]]

        with self.assertRaises(RuntimeError) as context:
            self.cs_index.resolve_by_doi("doi0")
            self.assertIn("Found several results", str(context.exception))

    def test_export_json(self):
        self.cs_index.export(self.closed_tmp_file.name, export_format="JSON")
        export_file = open(self.closed_tmp_file.name)
        export_file_lines = export_file.readlines()[0]

        self.assertEqual(json.dumps(self.cs_index.get_leaves_dict_list()), export_file_lines)

        export_file.close()

    def test_export_unknown(self):
        with self.assertRaises(NotImplementedError):
            self.cs_index.export(self.closed_tmp_file.name, export_format="UNKNOWN")

    @patch('album.core.model.catalog_index.RenderTree', return_value="")
    def test_visualize(self, rt_mock):
        self.cs_index.visualize()
        rt_mock.assert_called_once_with(self.cs_index.index)


if __name__ == '__main__':
    unittest.main()
