import json
import shutil
import tempfile
import unittest.mock
from pathlib import Path
from unittest.mock import patch

from anytree import Node

from hips.core.model.catalog import Catalog, CatalogIndex
from hips.core.model.configuration import HipsDefaultValues
from hips.core.model.hips_base import HipsClass
from test.unit.test_common import TestHipsCommon

sample_index = """{
  "children": [
    {
      "children": [
        {
          "children": [
            {
              "name": "testVersion",
              "doi": "doi0",
              "solution_name": "testName"
            }
          ],
          "name": "testName"
        }
      ],
      "name": "testGroup"
    }
  ],
  "name": "testCatalog"
}
"""
empty_index = """{
  "children": [],
  "name": "testCatalog"  
}"""


def populate_index(catalog):
    for i in range(0, 10):
        d = {}

        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, str(i))

        hips = HipsClass(d)

        # set a doi
        setattr(hips, "doi", "doi%s" % str(i))

        # set a deposit ID
        setattr(hips, "deposit_id", "deposit_id%s" % str(i))

        catalog.add(hips)

    return catalog


class TestCatalog(TestHipsCommon):

    def populate_index(self):
        self.catalog = populate_index(self.catalog)

    def setUp(self):
        self.tmp_dir = tempfile.gettempdir()
        self.catalog = Catalog("test", Path(self.tmp_dir).joinpath("testRepo"))

    def tearDown(self) -> None:
        try:
            Path(self.tmp_dir).joinpath(HipsDefaultValues.catalog_index_file_name.value).unlink()
        except FileNotFoundError:
            pass
        shutil.rmtree(Path(self.tmp_dir).joinpath("testRepo"), ignore_errors=True)

    # Actually rather an integration test
    def test__init__(self):
        new_catalog = self.catalog
        self.assertEqual(new_catalog.path, Path(self.tmp_dir).joinpath("testRepo"))
        self.assertIsNone(new_catalog.src)
        self.assertTrue(new_catalog.is_local)
        self.assertEqual(new_catalog.id, "test")
        self.assertEqual(str(new_catalog.catalog_index.index), str(Node("test", **{"version": "0.1.0"})))

    # Actually rather an integration test
    def test_add_and_len(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    def test_add_doi_already_present(self, get_solution_cache_path_file):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        tmp_file = tempfile.NamedTemporaryFile()
        get_solution_cache_path_file.side_effect = [Path(tmp_file.name)]

        d = {}
        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        hips = HipsClass(d)

        # this doi is already in index
        setattr(hips, "doi", "doi1")
        self.assertIsNotNone(self.catalog.resolve_doi("doi1"))

        with self.assertRaises(RuntimeError):
            self.catalog.add(hips)

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    def test_add_solution_already_present_no_overwrite(self, get_solution_cache_file_mock):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        tmp_file = tempfile.NamedTemporaryFile()
        get_solution_cache_file_mock.side_effect = [Path(tmp_file.name)]

        d = {}
        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        hips = HipsClass(d)

        with self.assertRaises(RuntimeError):
            self.catalog.add(hips)

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    def test_add_solution_already_present_overwrite(self, get_solution_cache_file_mock):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        tmp_file = tempfile.NamedTemporaryFile()
        get_solution_cache_file_mock.side_effect = [Path(tmp_file.name)]

        d = {}
        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        hips = HipsClass(d)

        self.catalog.add(hips, force_overwrite=True)
        self.assertEqual(len(self.catalog), 10)

    def test_remove(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        d = {}
        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        hips = HipsClass(d)

        self.catalog.remove(hips)
        self.assertEqual(len(self.catalog), 9)

    def test_remove_not_installed(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        d = {}
        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        hips = HipsClass(d)

        self.catalog.remove(hips)
        self.assertIn("WARNING - Solution not installed!", self.get_logs()[-1])
        self.assertEqual(len(self.catalog), 10)

    def test_remove_not_local(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        d = {}
        for key in HipsClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        hips = HipsClass(d)

        self.catalog.is_local = False
        self.catalog.remove(hips)
        self.assertIn("WARNING - Cannot remove entries", self.get_logs()[-1])
        self.assertEqual(len(self.catalog), 10)

    @patch('hips.core.model.catalog.Catalog.get_solution_cache_file')
    def test_resolve(self, get_solution_cache_file_mock):
        self.populate_index()
        tmp_file = tempfile.NamedTemporaryFile()
        get_solution_cache_file_mock.side_effect = [Path(tmp_file.name)]

        search_result = self.catalog.resolve("group0", "name0", "version0")

        self.assertEqual(search_result, Path(tmp_file.name))

    @patch('hips.core.model.catalog.Catalog.get_solution_cache_file')
    def test_resolve_in_index_but_no_file(self, get_solution_cache_file_mock):
        self.populate_index()
        get_solution_cache_file_mock.side_effect = [Path("pathDoesNotExist")]

        with self.assertRaises(FileNotFoundError):
            self.catalog.resolve("group0", "name0", "version0")

    @patch('hips.core.model.catalog.Catalog.get_solution_cache_file')
    @patch('hips.core.model.catalog.Catalog.download_solution_via_doi', return_value=True)
    def test_resolve_download_by_doi_if_present(self, download_doi_solution_mock, get_solution_cache_file_mock):
        self.populate_index()
        self.catalog.is_local = False
        tempfile.NamedTemporaryFile()
        get_solution_cache_file_mock.side_effect = [Path("pathDoesNotExist")]

        search_result = self.catalog.resolve("group0", "name0", "version0")
        download_doi_solution_mock.assert_called_once()

        self.assertEqual(search_result, Path("pathDoesNotExist"))

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    def test_resolve_doi(self, get_doi_cache_file_mock):
        self.populate_index()
        tmp_file = tempfile.NamedTemporaryFile()
        get_doi_cache_file_mock.side_effect = [Path(tmp_file.name)]

        search_result = self.catalog.resolve_doi("doi0")

        self.assertEqual(search_result, Path(tmp_file.name))

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    @patch('hips.core.model.catalog.Catalog.download_solution_via_doi')
    def test_resolve_doi_not_cached(self, download_doi_solution_mock, get_solution_cache_file_mock):
        self.populate_index()
        tmp_file = tempfile.NamedTemporaryFile()
        get_solution_cache_file_mock.side_effect = [Path("pathDoesNotExist")]

        download_doi_solution_mock.side_effect = [Path(tmp_file.name)]

        search_result = self.catalog.resolve_doi("doi0")

        download_doi_solution_mock.assert_called_once()
        self.assertEqual(search_result, Path(tmp_file.name))

    @unittest.skip("tested in hips_catalog.CatalogIndex.visualize")
    def test_visualize(self):
        pass

    def test_load_index(self):
        self.populate_index()

        cs_file = Path(self.tmp_dir).joinpath(HipsDefaultValues.catalog_index_file_name.value)
        with open(cs_file, "w+") as f:
            f.write(sample_index)

        self.assertTrue(len(self.catalog) == 10)  # its the old catalog
        self.catalog.index_path = cs_file  # path to "new" catalog
        self.catalog.load_index()
        self.assertTrue(len(self.catalog) == 1)  # now is the "new" catalog

    def test_refresh_index(self):
        cs_file = Path(self.tmp_dir).joinpath(HipsDefaultValues.catalog_index_file_name.value)
        with open(cs_file, "w+") as f:
            f.write(empty_index)

        self.catalog.index_path = cs_file
        self.catalog.load_index()
        self.assertTrue(len(self.catalog) == 0)

        with open(cs_file, "w+") as f:
            f.write(sample_index)

        self.assertTrue(self.catalog.refresh_index())
        self.assertTrue(len(self.catalog) == 1)

    def test_refresh_index_broken_src(self):
        self.catalog.src = "http://google.com/doesNotExist.ico"
        self.catalog.is_local = False

        self.assertFalse(self.catalog.refresh_index())

    def test_download_index(self):
        self.assertEqual(self.catalog.index_path.stat().st_size, 0)
        # todo: replace me
        self.catalog.src = "https://gitlab.com/ida-mdc/hips-catalog/-/raw/main/catalog_index?inline=false"
        self.catalog.is_local = False
        self.catalog.download_index()
        self.assertNotEqual(self.catalog.index_path.stat().st_size, 0)

    def test_download_index_not_downloadable(self):
        self.catalog.src = "http://google.com/doesNotExist.ico"
        self.catalog.is_local = False

        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    @patch('hips.core.model.catalog.get_index_src')
    def test_download_index_wrong_format(self, get_index_mock):

        get_index_mock.side_effect = [self.catalog.src]
        self.catalog.src = "https://www.google.com/favicon.ico"
        self.catalog.is_local = False

        with self.assertRaises(ValueError):
            self.catalog.download_index()

    def test_get_solution_cache_path(self):
        self.assertEqual(
            self.catalog.get_solution_cache_path("g", "n", "v"),
            self.catalog.path.joinpath(self.catalog.gnv_solution_prefix, "g", "n", "v")
        )

    def test_get_doi_cache_file(self):
        self.assertEqual(
            self.catalog.get_doi_cache_file("d"), self.catalog.path.joinpath(self.catalog.doi_solution_prefix, "d")
        )

    @unittest.skip("Needs to be implemented!")
    def test_list_installed(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_grp_name_version_from_file_structure(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_doi_to_grp_name_version(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_solution_cache_file(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_download_solution_via_doi(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_download_solution(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_download(self):
        # ToDo: implement
        pass

    @unittest.skip("tested in hips_catalog.CatalogIndex.__len__")
    def test__len__(self):
        pass


class TestHipsCatalogIndex(TestHipsCommon):
    def setUp(self):
        self.tmp_dir = tempfile.gettempdir()

        # fill index file
        cs_file = Path(self.tmp_dir).joinpath(HipsDefaultValues.catalog_index_file_name.value)
        with open(cs_file, "w+") as f:
            f.write(sample_index)
        self.cs_file = cs_file

        # fill empty_index file
        self.cs_file_index_empty = Path(self.tmp_dir).joinpath("empty_index_file")
        with open(self.cs_file_index_empty, "w+") as f:
            f.write(empty_index)

        # fill emtpy_file
        self.cs_file_empty = Path(self.tmp_dir).joinpath("empty_file")
        self.cs_file_empty.touch()

        self.cs_index = CatalogIndex("test", self.cs_file)

    def tearDown(self) -> None:
        try:
            Path(self.tmp_dir).joinpath(HipsDefaultValues.catalog_index_file_name.value).unlink()
            Path(self.tmp_dir).joinpath("empty_index_file").unlink()
            Path(self.tmp_dir).joinpath("empty_file").unlink()
        except FileNotFoundError:
            pass

    def test__init__(self):
        self.assertEqual(len(self.cs_index), 1)

    def test__init__index_given(self):
        cs_index = CatalogIndex("test", self.cs_file, index=Node("IndexGiven", **{"version": "0.1.0"}))

        self.assertEqual(len(cs_index), 0)

    @unittest.skip("Needs to be implemented!")
    def test__len__(self):
        # ToDo: implement
        pass

    def test_load(self):
        self.assertEqual(len(self.cs_index), 1)
        self.cs_index.load(self.cs_file_index_empty)
        self.assertEqual(len(self.cs_index), 0)

    def test_load_empty_file(self):
        self.assertEqual(len(self.cs_index), 1)
        self.cs_index.load(self.cs_file_empty)
        self.assertEqual(len(self.cs_index), 1)

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
        self.assertEqual(len(self.cs_index), 1)

        # updated version
        node_attrs = {"name": "testName", "group": "testGroup", "version": "testVersion", "newAttr": "newAttrVal"}
        self.cs_index.update(node_attrs)

        # check changes
        self.assertEqual(len(self.cs_index), 1)
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
        self.assertEqual(len(self.cs_index), 1)

        # updated version
        node_attrs = {"name": "testName", "group": "testGroup", "version": "testVersion2"}
        self.cs_index.update(node_attrs)

        # check
        self.assertEqual(len(self.cs_index), 2)
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
        self.assertEqual(len(self.cs_index), 1)

    def test_get_leaves_dict_list(self):
        l_dict_list = self.cs_index.get_leaves_dict_list()
        self.assertEqual(len(l_dict_list), 1)

    def test_resolve_hips_by_name_version_and_group(self):
        self.assertIsNotNone(
            self.cs_index.resolve_hips_by_name_version_and_group("testName", "testVersion", "testGroup")
        )

    def test_resolve_hips_by_name_version_and_group_no_leaf(self):
        r = self.cs_index.resolve_hips_by_name_version_and_group("testName", "testVersion", "testGroup")
        self.assertIsNotNone(r)
        Node("wrongNode", parent=r)  # resolving not a leaf any more
        with self.assertRaises(RuntimeError):
            self.cs_index.resolve_hips_by_name_version_and_group("testName", "testVersion", "testGroup")

    def test_resolve_hips_by_doi(self):
        self.assertIsNotNone(
            self.cs_index.resolve_hips_by_doi("doi0")
        )

    def test_test_resolve_hips_by_doi_no_leaf(self):
        r = self.cs_index.resolve_hips_by_doi("doi0")
        self.assertIsNotNone(r)
        Node("wrongNode", parent=r)  # resolving not a leaf any more

        with self.assertRaises(RuntimeError) as context:
            self.cs_index.resolve_hips_by_doi("doi0")
            self.assertIn("Ambiguous results", str(context.exception))

    @patch('hips.core.model.catalog.CatalogIndex._find_all_nodes_by_attribute')
    def test_test_resolve_hips_by_doi_two_doi(self, fanba_mock):
        fanba_mock.side_effect = [[Node("new1"), Node("new2")]]

        with self.assertRaises(RuntimeError) as context:
            self.cs_index.resolve_hips_by_doi("doi0")
            self.assertIn("Found several results", str(context.exception))

    def test_export_json(self):
        self.setUp()
        with tempfile.NamedTemporaryFile() as f:
            self.cs_index.export(f.name, export_format="JSON")
            export_file = open(f.name).readlines()[0]

            self.assertEqual(json.dumps(self.cs_index.get_leaves_dict_list()), export_file)

    @patch('hips.core.model.catalog.RenderTree', return_value="")
    def test_visualize(self, rt_mock):
        self.cs_index.visualize()
        rt_mock.assert_called_once_with(self.cs_index.index)


if __name__ == '__main__':
    unittest.main()
