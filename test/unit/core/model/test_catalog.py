import json
import os
import unittest.mock
from pathlib import Path
from unittest.mock import patch

from anytree import Node

from hips.core.model.catalog import Catalog, CatalogIndex
from hips.core.model.default_values import HipsDefaultValues
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


class TestCatalog(TestHipsCommon):

    @patch('hips.core.model.hips_base.Environment.__init__', return_value=None)
    def populate_index(self, _, r=10):
        for i in range(0, r):
            d = {}

            for key in HipsClass.deploy_keys:
                d[key] = "%s%s" % (key, str(i))

            hips = HipsClass(d)

            # set a doi
            setattr(hips, "doi", "doi%s" % str(i))

            # set a deposit ID
            setattr(hips, "deposit_id", "deposit_id%s" % str(i))

            self.catalog.add(hips)

    def setUp(self):
        self.catalog = Catalog("test", Path(self.tmp_dir.name).joinpath("testRepo"))

    def tearDown(self) -> None:
        super().tearDown()

    # Actually rather an integration test
    def test__init__(self):
        new_catalog = self.catalog
        self.assertEqual(new_catalog.path, Path(self.tmp_dir.name).joinpath("testRepo"))
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

        get_solution_cache_path_file.side_effect = [Path(self.closed_tmp_file.name)]

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

        get_solution_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

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

        get_solution_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

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

    @patch('hips.core.model.catalog.Catalog.get_solution_file')
    def test_resolve(self, get_solution_file_mock):
        self.populate_index()
        get_solution_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        search_result = self.catalog.resolve("group0", "name0", "version0")

        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    @patch('hips.core.model.catalog.Catalog.get_solution_file')
    def test_resolve_in_index_but_no_file(self, get_solution_file_mock):
        self.populate_index()
        get_solution_file_mock.side_effect = [Path("pathDoesNotExist")]

        with self.assertRaises(FileNotFoundError):
            self.catalog.resolve("group0", "name0", "version0")

    @patch('hips.core.model.catalog.Catalog.get_solution_file')
    @patch('hips.core.model.catalog.Catalog.download_solution_via_doi', return_value=Path("pathDoesNotExist"))
    def test_resolve_download_by_doi_if_present(self, download_doi_solution_mock, get_solution_file_mock):
        self.populate_index()
        self.catalog.is_local = False
        get_solution_file_mock.side_effect = [Path("pathDoesNotExist")]

        search_result = self.catalog.resolve("group0", "name0", "version0")
        download_doi_solution_mock.assert_called_once()

        self.assertEqual(Path("pathDoesNotExist"), search_result)

    @patch('hips.core.model.catalog.Catalog.get_solution_file')
    @patch('hips.core.model.catalog.Catalog.download_solution_via_doi', return_value=True)
    def test_resolve_not_download_by_doi_on_flag(self, download_doi_solution_mock, get_solution_file_mock):
        self.populate_index()
        self.catalog.is_local = False
        get_solution_file_mock.side_effect = [Path("pathDoesNotExist")]

        with self.assertRaises(FileNotFoundError):
            self.catalog.resolve("group0", "name0", "version0", download=False)

        download_doi_solution_mock.assert_not_called()

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    def test_resolve_doi(self, get_doi_cache_file_mock):
        self.populate_index()
        get_doi_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        search_result = self.catalog.resolve_doi("doi0")

        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    @patch('hips.core.model.catalog.Catalog.download_solution_via_doi')
    def test_resolve_doi_not_cached(self, download_doi_solution_mock, get_solution_cache_file_mock):
        self.populate_index()
        get_solution_cache_file_mock.side_effect = [Path("pathDoesNotExist")]

        download_doi_solution_mock.side_effect = [Path(self.closed_tmp_file.name)]

        search_result = self.catalog.resolve_doi("doi0")

        download_doi_solution_mock.assert_called_once()
        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    @patch('hips.core.model.catalog.Catalog.get_doi_cache_file')
    @patch('hips.core.model.catalog.Catalog.download_solution_via_doi')
    def test_resolve_doi_not_cached_no_download(self, download_doi_solution_mock, get_solution_cache_file_mock):
        self.populate_index()
        get_solution_cache_file_mock.side_effect = [Path("pathDoesNotExist")]

        download_doi_solution_mock.side_effect = [Path(self.closed_tmp_file.name)]

        with self.assertRaises(FileNotFoundError):
            self.catalog.resolve_doi("doi0", download=False)

        download_doi_solution_mock.assert_not_called()

    @unittest.skip("tested in hips_catalog.CatalogIndex.visualize")
    def test_visualize(self):
        pass

    def test_load_index(self):
        self.populate_index()

        cs_file = Path(self.tmp_dir.name).joinpath(HipsDefaultValues.catalog_index_file_name.value)
        with open(cs_file, "w+") as f:
            f.write(sample_index)

        self.assertTrue(len(self.catalog) == 10)  # its the old catalog
        self.catalog.index_path = cs_file  # path to "new" catalog
        self.catalog.load_index()
        self.assertTrue(len(self.catalog) == 1)  # now is the "new" catalog

    def test_refresh_index(self):
        cs_file = Path(self.tmp_dir.name).joinpath(HipsDefaultValues.catalog_index_file_name.value)
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

    def test_get_solution_path(self):
        self.assertEqual(
            self.catalog.get_solution_path("g", "n", "v"),
            self.catalog.path.joinpath(self.catalog.gnv_solution_prefix, "g", "n", "v")
        )

    def test_get_solution_zip(self):
        res = self.catalog.path.joinpath(HipsDefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        self.assertEqual(res, self.catalog.get_solution_zip("g", "n", "v"))

    def test_get_doi_cache_file(self):
        self.assertEqual(
            self.catalog.get_doi_cache_file("d"), self.catalog.path.joinpath(self.catalog.doi_solution_prefix, "d")
        )

    def test_list_installed(self):
        self.populate_index(r=4)

        # create solution files installed via g, n, v
        for i in range(0, 2):
            p = self.catalog.get_solution_zip("group" + str(i), "name" + str(i), "version" + str(i))
            p.mkdir(parents=True)
            p.touch()

        # create solution files installed via doi
        for i in range(2, 4):
            p = self.catalog.get_doi_cache_file("doi" + str(i))
            p.mkdir(parents=True)
            p.touch()

        r = [
            {"group": "group0", "name": "name0", "version": "version0"},
            {"group": "group1", "name": "name1", "version": "version1"},
            {"group": "group2", "name": "name2", "version": "version2"},
            {"group": "group3", "name": "name3", "version": "version3"}]

        self.assertEqual(r, self.catalog.list_installed())

    def test_get_grp_name_version_from_file_structure(self):
        self.populate_index(r=2)

        grp_dir = "group0"
        solution_dir = "name0"
        version_dir = "version0"

        node = self.catalog.catalog_index.index.leaves[0]
        res = {
            "group": node.solution_group,
            "name": node.solution_name,
            "version": node.solution_version,
        }

        self.assertEqual(res, self.catalog.get_grp_name_version_from_file_structure(grp_dir, solution_dir, version_dir))

    def test_doi_to_grp_name_version(self):
        self.populate_index(r=2)

        doi = "doi0"

        node = self.catalog.catalog_index.index.leaves[0]
        res = {
            "group": node.solution_group,
            "name": node.solution_name,
            "version": node.solution_version,
        }

        self.assertEqual(res, self.catalog.doi_to_grp_name_version(doi))


    @unittest.skip("Needs to be implemented!")
    def test_download_solution_via_doi(self):
        # ToDo: implement
        pass

    @patch("hips.core.model.catalog.download_resource", return_value=None)
    @patch("hips.core.model.catalog.unzip_archive", return_value=Path("a/Path"))
    def test_download_solution(self, unzip_mock, dl_mock):
        self.catalog.src = "NonsenseUrl.git"

        dl_url = "NonsenseUrl" + "/-/raw/main/solutions/g/n/v/gnv.zip"
        dl_path = self.catalog.path.joinpath(
            HipsDefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip"
        )
        res = Path("a/Path").joinpath(HipsDefaultValues.solution_default_name.value)

        self.assertEqual(res, self.catalog.download_solution("g", "n", "v"))
        dl_mock.assert_called_once_with(dl_url, dl_path)
        unzip_mock.assert_called_once_with(dl_path)

    def test_download(self):
        self.catalog.src = HipsDefaultValues.catalog_url.value
        self.catalog.is_local = False

        dl_path = Path(self.tmp_dir.name).joinpath("test")

        # folder already exists with file in it
        os.mkdir(dl_path)
        blocking_file = dl_path.joinpath("blocking_file")
        blocking_file.touch()

        self.catalog.download(dl_path, force_download=True)

        self.assertFalse(blocking_file.exists())
        self.assertTrue(dl_path.stat().st_size > 0)

    @unittest.skip("tested in hips_catalog.CatalogIndex.__len__")
    def test__len__(self):
        pass


if __name__ == '__main__':
    unittest.main()
