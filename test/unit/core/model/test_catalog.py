import os
import unittest.mock
from pathlib import Path
from unittest.mock import patch

from anytree import Node

from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.model.album_base import AlbumClass
from test.unit.test_unit_common import TestUnitCommon

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


class TestCatalog(TestUnitCommon):

    @patch('album.core.model.album_base.Environment.__init__', return_value=None)
    def populate_index(self, _, r=10):
        for i in range(0, r):
            d = {}

            for key in AlbumClass.deploy_keys:
                d[key] = "%s%s" % (key, str(i))

            solution = AlbumClass(d)

            # set a doi
            setattr(solution, "doi", "doi%s" % str(i))

            # set a deposit ID
            setattr(solution, "deposit_id", "deposit_id%s" % str(i))

            self.catalog.add(solution)

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

    @patch('album.core.model.catalog.Catalog.get_doi_cache_file')
    def test_add_doi_already_present(self, get_solution_cache_path_file):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        get_solution_cache_path_file.side_effect = [Path(self.closed_tmp_file.name)]

        d = {}
        for key in AlbumClass.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        solution = AlbumClass(d)

        # this doi is already in index
        setattr(solution, "doi", "doi1")
        self.assertIsNotNone(self.catalog.resolve_doi("doi1"))

        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    @patch('album.core.model.catalog.Catalog.get_doi_cache_file')
    def test_add_solution_already_present_no_overwrite(self, get_solution_cache_file_mock):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        get_solution_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        d = {}
        for key in AlbumClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = AlbumClass(d)

        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    @patch('album.core.model.catalog.Catalog.get_doi_cache_file')
    def test_add_solution_already_present_overwrite(self, get_solution_cache_file_mock):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        get_solution_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        d = {}
        for key in AlbumClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = AlbumClass(d)

        self.catalog.add(solution, force_overwrite=True)
        self.assertEqual(len(self.catalog), 10)

    def test_remove(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        d = {}
        for key in AlbumClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = AlbumClass(d)

        self.catalog.remove(solution)
        self.assertEqual(len(self.catalog), 9)

    def test_remove_not_installed(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        d = {}
        for key in AlbumClass.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        solution = AlbumClass(d)

        self.catalog.remove(solution)
        self.assertIn("WARNING - Solution not installed!", self.get_logs()[-1])
        self.assertEqual(len(self.catalog), 10)

    def test_remove_not_local(self):
        self.populate_index()
        self.assertEqual(len(self.catalog), 10)

        d = {}
        for key in AlbumClass.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = AlbumClass(d)

        self.catalog.is_local = False
        self.catalog.remove(solution)
        self.assertIn("WARNING - Cannot remove entries", self.get_logs()[-1])
        self.assertEqual(len(self.catalog), 10)

    @patch('album.core.model.catalog.Catalog.get_solution_file')
    def test_resolve_nothing_found(self, get_solution_file_mock):
        get_solution_file_mock.return_value = None
        self.assertIsNone(self.catalog.resolve("a", "b", "c"))

    @patch('album.core.model.catalog.Catalog.get_solution_file')
    def test_resolve_doi_nothing_found(self, get_solution_file_mock):
        get_solution_file_mock.return_value = None
        self.assertIsNone(self.catalog.resolve_doi("a"))

    @patch('album.core.model.catalog.Catalog.get_solution_file')
    def test_resolve(self, get_solution_file_mock):
        self.populate_index()
        get_solution_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        search_result = self.catalog.resolve("group0", "name0", "version0")

        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    @patch('album.core.model.catalog.Catalog.get_doi_cache_file')
    def test_resolve_doi(self, get_doi_cache_file_mock):
        self.populate_index()
        get_doi_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        search_result = self.catalog.resolve_doi("doi0")

        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    @unittest.skip("tested in test_catalog_index.CatalogIndex.visualize")
    def test_visualize(self):
        pass

    def test_load_index(self):
        self.populate_index()

        cs_file = Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_index_file_name.value)
        with open(cs_file, "w+") as f:
            f.write(sample_index)

        self.assertTrue(len(self.catalog) == 10)  # its the old catalog
        self.catalog.index_path = cs_file  # path to "new" catalog
        self.catalog.load_index()
        self.assertTrue(len(self.catalog) == 1)  # now is the "new" catalog

    def test_refresh_index(self):
        cs_file = Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_index_file_name.value)
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
        self.catalog.src = "https://gitlab.com/album-app/capture-knowledge/-/raw/main/catalog_index?inline=false"
        self.catalog.is_local = False
        self.catalog.download_index()
        self.assertNotEqual(self.catalog.index_path.stat().st_size, 0)

    def test_download_index_not_downloadable(self):
        self.catalog.src = "http://google.com/doesNotExist.ico"
        self.catalog.is_local = False

        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    @patch('album.core.model.catalog.get_index_src')
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
        res = self.catalog.path.joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        self.assertEqual(res, self.catalog.get_solution_zip("g", "n", "v"))

    def test_get_doi_cache_file(self):
        self.assertEqual(
            self.catalog.get_doi_cache_file("d"), self.catalog.path.joinpath(self.catalog.doi_solution_prefix, "d")
        )

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

    @patch("album.core.model.catalog.download_resource", return_value=None)
    @patch("album.core.model.catalog.unzip_archive", return_value=Path("a/Path"))
    def test_download_solution(self, unzip_mock, dl_mock):
        self.catalog.src = "NonsenseUrl.git"

        dl_url = "NonsenseUrl" + "/-/raw/main/solutions/g/n/v/gnv.zip"
        dl_path = self.catalog.path.joinpath(
            DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip"
        )
        res = Path("a/Path").joinpath(DefaultValues.solution_default_name.value)

        self.assertEqual(res, self.catalog.download_solution("g", "n", "v"))
        dl_mock.assert_called_once_with(dl_url, dl_path)
        unzip_mock.assert_called_once_with(dl_path)

    def test_download(self):
        self.catalog.src = DefaultValues.catalog_url.value
        self.catalog.is_local = False

        dl_path = Path(self.tmp_dir.name).joinpath("test")

        # folder already exists with file in it
        os.mkdir(dl_path)
        blocking_file = dl_path.joinpath("blocking_file")
        blocking_file.touch()

        self.catalog.download(dl_path, force_download=True)

        self.assertFalse(blocking_file.exists())
        self.assertTrue(dl_path.stat().st_size > 0)

    @unittest.skip("tested in test_catalog_index.CatalogIndex.__len__")
    def test__len__(self):
        pass


if __name__ == '__main__':
    unittest.main()
