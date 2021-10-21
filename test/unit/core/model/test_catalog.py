import os
import shutil
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.model.configuration import Configuration

from album.core.controller.migration_manager import MigrationManager

from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.model.catalog import Catalog
from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.core.model.solution import Solution
from test.unit.test_unit_common import TestUnitCommon

empty_index = """{
  "version": "0.1.0",
  "name": "testCatalog"  
}"""


class TestCatalog(TestUnitCommon):

    @patch('album.core.model.solution.Environment.__init__', return_value=None)
    def populate_index(self, _, r=10):
        for i in range(0, r):
            d = self.get_solution_dict()

            for key in ["group", "name", "version", "doi", "deposit_id"]:
                d[key] = "%s%s" % (key, str(i))

            solution = Solution(d)

            # set a doi
            setattr(solution, "doi", "doi%s" % str(i))

            # set a deposit ID
            setattr(solution, "deposit_id", "deposit_id%s" % str(i))

            self.catalog.add(solution)

    def setUp(self):
        super().setUp()
        Configuration().setup(base_cache_path=Path(self.tmp_dir.name).joinpath("album"), configuration_file_path=self.tmp_dir.name)
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        CatalogHandler.create_new_catalog(catalog_src, "test")
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)
        self.catalog = Catalog(0, "test", catalog_src, catalog_path)
        MigrationManager().load_index(self.catalog)

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

    # Actually rather an integration test
    def test__init__(self):
        new_catalog = self.catalog
        self.assertEqual(new_catalog.path, Path(self.tmp_dir.name).joinpath("testRepo"))
        self.assertIsNotNone(new_catalog.src)
        self.assertTrue(new_catalog.is_local())
        self.assertEqual(new_catalog.name, "test")
        self.assertEqual(str(new_catalog.get_meta_information()), "{\'name\': \'test\', \'version\': \'0.1.0\'}")

    # Actually rather an integration test
    def test_add_and_len(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_add_doi_already_present(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        solution = Solution(d)

        # this doi is already in index
        setattr(solution, "doi", "doi1")
        self.assertIsNotNone(self.catalog.resolve_doi("doi1"))

        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    def test_add_solution_already_present_no_overwrite(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    @patch('album.core.model.catalog.Catalog.get_solution_file')
    def test_add_solution_already_present_overwrite(self, get_solution_cache_file_mock):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        get_solution_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        self.catalog.add(solution, force_overwrite=True)
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_remove(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        self.catalog.remove(solution)
        self.assertEqual(len(self.catalog.catalog_index), 9)

    def test_remove_not_installed(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        solution = Solution(d)

        self.catalog.remove(solution)
        self.assertIn("WARNING - Solution not installed!", self.get_logs()[-1])
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_remove_not_local(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        self.catalog.is_local = MagicMock(return_value=False)
        self.catalog.remove(solution)
        self.assertIn("WARNING - Cannot remove entries", self.get_logs()[-1])
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_resolve_nothing_found(self):
        get_solution_by_coordinates = MagicMock(return_value=None)
        self.catalog.catalog_index.get_solution_by_coordinates = get_solution_by_coordinates

        # call & assert
        self.assertIsNone(self.catalog.resolve(Coordinates("a", "b", "c")))
        get_solution_by_coordinates.assert_called_once_with(Coordinates("a", "b", "c"))

    def test_resolve_doi_nothing_found(self):
        get_solution_by_doi = MagicMock(return_value=None)
        self.catalog.catalog_index.get_solution_by_doi = get_solution_by_doi

        # call & assert
        self.assertIsNone(self.catalog.resolve_doi("a"))
        get_solution_by_doi.assert_called_once_with("a")

    @patch('album.core.model.catalog.Catalog.get_solution_file')
    def test_resolve(self, get_solution_file_mock):
        self.populate_index()
        get_solution_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        # call
        search_result = self.catalog.resolve(Coordinates("group0", "name0", "version0"))

        # assert
        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    def test_resolve_doi(self):

        self.catalog.catalog_index.get_solution_by_doi = MagicMock(
            return_value={"path": self.closed_tmp_file.name, "group": "group0", "name": "name0", "version": "version0"})

        search_result = self.catalog.resolve_doi("doi0")

        self.assertEqual(Path(self.catalog.path).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "group0", "name0", "version0", DefaultValues.solution_default_name.value), search_result)

    @unittest.skip("Needs to be implemented!")
    def test_download_index(self):
        # ToDo: implement
        pass

    def test_download_index_not_downloadable(self):
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               "http://google.com/doesNotExist.ico")
        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    def test_download_index_wrong_format(self):
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               "https://www.google.com/favicon.ico")

        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    def test_get_solution_path(self):
        self.assertEqual(
            self.catalog.get_solution_path(Coordinates("g", "n", "v")),
            self.catalog.path.joinpath(self.catalog.gnv_solution_prefix, "g", "n", "v")
        )

    def test_get_solution_zip(self):
        res = self.catalog.path.joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        self.assertEqual(res, self.catalog.get_solution_zip(Coordinates("g", "n", "v")))

    @unittest.skip("Needs to be implemented!")
    def test_download_solution_via_doi(self):
        # ToDo: implement
        pass

    @patch("album.core.model.catalog.download_resource", return_value=None)
    @patch("album.core.model.catalog.unzip_archive", return_value=Path("a/Path"))
    def test_download_solution(self, unzip_mock, dl_mock):
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               "http://NonsenseUrl.git")
        self.catalog.is_cache = MagicMock(return_value=False)

        dl_url = "http://NonsenseUrl" + "/-/raw/main/solutions/g/n/v/g_n_v.zip"
        dl_path = self.catalog.path.joinpath(
            DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip"
        )
        res = Path("a/Path").joinpath(DefaultValues.solution_default_name.value)

        self.assertEqual(res, self.catalog.retrieve_solution(Coordinates("g", "n", "v")))
        dl_mock.assert_called_once_with(dl_url, dl_path)
        unzip_mock.assert_called_once_with(dl_path)

    def test_download(self):
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               DefaultValues.default_catalog_src.value)

        dl_path = Path(self.tmp_dir.name).joinpath("test")

        # folder already exists with file in it
        os.mkdir(dl_path)
        blocking_file = dl_path.joinpath("blocking_file")
        blocking_file.touch()

        repo = self.catalog.retrieve_catalog(dl_path, force_retrieve=True)
        self.assertIsNotNone(repo)
        repo.close()

        self.assertFalse(blocking_file.exists())
        self.assertTrue(dl_path.stat().st_size > 0)


if __name__ == '__main__':
    unittest.main()
