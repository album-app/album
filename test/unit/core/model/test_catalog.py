import os
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.default_values import DefaultValues
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCatalog(TestUnitCoreCommon):

    def populate_index(self, r=10):
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
        self.create_album_test_instance(init_catalogs=False, init_collection=True)
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        CatalogHandler.create_new_catalog(catalog_src, "test")
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        self.catalog = Catalog(0, "test", src=catalog_src, path=catalog_path)
        self.catalog.update_index_cache()
        self.catalog.load_index()
        self.collection_manager.catalogs().set_version(self.catalog)

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

    def test__init__(self):
        new_catalog = self.catalog
        self.assertEqual(new_catalog._path, Path(self.tmp_dir.name).joinpath('testPath'))
        self.assertIsNotNone(new_catalog._src)
        self.assertTrue(new_catalog.is_local())
        self.assertEqual(new_catalog._name, 'test')
        self.assertEqual('{\'name\': \'test\', \'version\': \'0.1.0\'}', str(new_catalog.get_meta_information()))

    @unittest.skip("Needs to be implemented!")
    def test_update_index_cache_if_possible(self):
        pass

    @patch('album.core.model.catalog.force_remove')
    def test_update_index_cache_remote_catalog_src_deleted(self, force_remove_mock):
        self.catalog._src = "https://mycatalog.org"
        # mock
        copy_index_from_src_to_cache = MagicMock(return_value=True)
        self.catalog.copy_index_from_src_to_cache = copy_index_from_src_to_cache

        download_index = MagicMock(return_value=False)
        self.catalog.download_index = download_index

        # call
        self.assertTrue(self.catalog.update_index_cache())

        # assert
        force_remove_mock.assert_called_once()
        copy_index_from_src_to_cache.assert_not_called()
        download_index.assert_called_once()

    @patch('album.core.model.catalog.force_remove')
    def test_update_index_cache_remote_catalog(self, force_remove_mock):
        self.catalog._src = "https://mycatalog.org"
        # mock
        copy_index_from_src_to_cache = MagicMock(return_value=True)
        self.catalog.copy_index_from_src_to_cache = copy_index_from_src_to_cache

        download_index = MagicMock(return_value=True)
        self.catalog.download_index = download_index

        # call
        self.assertTrue(self.catalog.update_index_cache())

        # assert
        force_remove_mock.assert_not_called()
        copy_index_from_src_to_cache.assert_not_called()
        download_index.assert_called_once()

    @patch('album.core.model.catalog.force_remove')
    def test_update_index_cache_local_catalog(self, force_remove_mock):
        # mock
        copy_index_from_src_to_cache = MagicMock(return_value=True)
        self.catalog.copy_index_from_src_to_cache = copy_index_from_src_to_cache

        download_index = MagicMock(return_value=True)
        self.catalog.download_index = download_index

        # call
        self.assertTrue(self.catalog.update_index_cache())

        # assert
        force_remove_mock.assert_not_called()
        copy_index_from_src_to_cache.assert_called_once()
        download_index.assert_not_called()

    def test_update_index_cache_cache_catalog(self):
        self.catalog._src = None  # set to cache only catalog

        # call
        self.assertFalse(self.catalog.update_index_cache())

    def test_add_and_len(self):
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

    def test_add_doi_already_present(self):
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "new")

        solution = Solution(d)

        # this doi is already in index
        solution._setup.doi = 'doi1'

        # call
        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    def test_add_solution_already_present_no_overwrite(self):
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        # call
        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    @patch('album.core.controller.collection.solution_handler.SolutionHandler.get_solution_file')
    def test_add_solution_already_present_overwrite(self, get_solution_cache_file_mock):
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

        get_solution_cache_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        # call
        self.catalog.add(solution, force_overwrite=True)

        # assert
        self.assertEqual(len(self.catalog._catalog_index), 10)

    def test_remove(self):
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)
        # call
        self.catalog.remove(solution)

        # assert
        self.assertEqual(len(self.catalog._catalog_index), 9)

    def test_remove_not_installed(self):
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "new")

        solution = Solution(d)

        # call
        self.catalog.remove(solution)

        # assert
        self.assertIn("WARNING - Solution not installed!", self.get_logs()[-1])
        self.assertEqual(len(self.catalog._catalog_index), 10)

    def test_remove_not_local(self):
        # prepare
        self.populate_index()
        self.assertEqual(len(self.catalog._catalog_index), 10)

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)
        self.catalog.is_local = MagicMock(return_value=False)

        # call
        self.catalog.remove(solution)

        # assert
        self.assertIn("WARNING - Cannot remove entries", self.get_logs()[-1])
        self.assertEqual(len(self.catalog._catalog_index), 10)

    def test_copy_index_from_src_to_cache(self):
        # prepare
        self.catalog._src.joinpath("album_catalog_index.db").touch()
        self.catalog._src.joinpath("album_catalog_index.json").touch()

        Path(self.catalog._path).joinpath("album_catalog_index.db").unlink()
        Path(self.catalog._path).joinpath("album_catalog_index.json").unlink()

        self.assertFalse(Path(self.catalog._path).joinpath("album_catalog_index.db").exists())
        self.assertFalse(Path(self.catalog._path).joinpath("album_catalog_index.json").exists())

        # deliberately not mocking copy call
        self.assertTrue(self.catalog.copy_index_from_src_to_cache())

        # assert
        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.json").exists())

    def test_copy_index_from_src_to_cache_no_db(self):
        # prepare
        self.catalog._src.joinpath("album_catalog_index.json").touch()

        Path(self.catalog._path).joinpath("album_catalog_index.db").unlink()
        Path(self.catalog._path).joinpath("album_catalog_index.json").unlink()

        self.assertFalse(Path(self.catalog._path).joinpath("album_catalog_index.db").exists())
        self.assertFalse(Path(self.catalog._path).joinpath("album_catalog_index.json").exists())

        # deliberately not mocking copy call
        self.assertTrue(self.catalog.copy_index_from_src_to_cache())

        # assert
        self.assertFalse(Path(self.catalog._path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.json").exists())

    def test_copy_index_from_src_to_cache_db_deleted(self):
        # prepare
        self.catalog._src.joinpath("album_catalog_index.json").touch()

        Path(self.catalog._path).joinpath("album_catalog_index.db").touch()
        Path(self.catalog._path).joinpath("album_catalog_index.json").touch()

        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.json").exists())

        # deliberately not mocking copy call
        self.assertFalse(self.catalog.copy_index_from_src_to_cache())

        # assert
        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog._path).joinpath("album_catalog_index.json").exists())

    def test_copy_index_from_cache_to_src(self):
        # prepare
        self.catalog._index_path.touch()
        self.catalog._path.joinpath("album_solution_list.json").touch()

        self.assertFalse(Path(self.catalog._src).joinpath("album_catalog_index.db").exists())
        self.assertFalse(Path(self.catalog._src).joinpath("album_solution_list.json").exists())

        # deliberately not mocking copy call
        self.catalog.copy_index_from_cache_to_src()

        # assert
        self.assertTrue(Path(self.catalog._src).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog._src).joinpath("album_solution_list.json").exists())

    @unittest.skip("Needs to be implemented!")
    def test_download_index(self):
        # ToDo: implement
        pass

    def test_download_index_not_downloadable(self):
        self.catalog = Catalog(self.catalog._catalog_id, self.catalog._name, self.catalog._path,
                               "http://google.com/doesNotExist.ico")

        # call
        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    def test_download_index_wrong_format(self):
        self.catalog = Catalog(self.catalog._catalog_id, self.catalog._name, self.catalog._path,
                               "https://www.google.com/favicon.ico")

        # call
        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    def test_retrieve_catalog(self):
        # prepare
        self.catalog = Catalog(self.catalog._catalog_id, self.catalog._name, self.catalog._path,
                               DefaultValues.default_catalog_src.value)

        dl_path = Path(self.tmp_dir.name).joinpath("test")

        # folder already exists with file in it
        os.mkdir(dl_path)
        blocking_file = dl_path.joinpath("blocking_file")
        blocking_file.touch()

        # call
        repo = self.catalog.retrieve_catalog(dl_path, force_retrieve=True)

        # assert
        self.assertIsNotNone(repo)
        repo.close()

        self.assertFalse(blocking_file.exists())
        self.assertTrue(dl_path.stat().st_size > 0)

    @patch('album.core.model.catalog.write_dict_to_json')
    def test_write_catalog_meta_information(self, write_dict_to_json_mock):
        self.catalog.write_catalog_meta_information()

        write_dict_to_json_mock.assert_called_once_with(
            self.catalog._path.joinpath("album_catalog_index.json"),
            {"name": self.catalog._name, "version": self.catalog._version}
        )

    def test_get_meta_information(self):
        self.assertEqual(
            self.catalog.get_meta_information(),
            {"name": self.catalog._name, "version": self.catalog._version}
        )


if __name__ == '__main__':
    unittest.main()
