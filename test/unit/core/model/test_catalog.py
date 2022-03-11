import os
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.model.catalog import Catalog, retrieve_index_files_from_src
from album.core.model.catalog_index import CatalogIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestCatalogAndCollectionCommon


class TestCatalog(TestCatalogAndCollectionCommon):

    def setUp(self):
        super().setUp()
        self.setup_collection(False, True)
        self.catalog = self.setup_catalog_no_git()
        self.album_controller.collection_manager().catalogs().set_version(self.catalog)

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

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

    def test__init__(self):
        new_catalog = self.catalog
        self.assertEqual(new_catalog._path, Path(self.tmp_dir.name).joinpath('testPath'))
        self.assertIsNotNone(new_catalog._src)
        self.assertTrue(new_catalog.is_local())
        self.assertEqual(new_catalog._name, 'test')
        self.assertDictEqual(self.get_catalog_meta_dict("test"), new_catalog.get_meta_information())

    @unittest.skip("Needs to be implemented!")
    def test_update_index_cache_if_possible(self):
        pass

    def test_update_index_cache(self):
        self.catalog._src = "https://mycatalog.org"
        # mock
        _download_index = MagicMock(return_value=False)
        self.catalog._update_index_cache = _download_index

        dispose = MagicMock()
        self.catalog.dispose = dispose

        # call
        self.assertTrue(self.catalog.update_index_cache(self.tmp_dir.name))

        # assert
        dispose.assert_called_once()
        _download_index.assert_called_once()

    def test_update_index_cache_cache_catalog(self):
        self.catalog._src = None  # set to cache only catalog

        # mock
        _update_index_cache = MagicMock()
        self.catalog._update_index_cache = _update_index_cache

        # call
        self.assertFalse(self.catalog.update_index_cache(self.tmp_dir.name))

        # assert
        _update_index_cache.assert_not_called()

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
        self.assertEqual(9, len(self.catalog._catalog_index))

    def test_remove_not_installed(self):
        self.populate_index()
        self.assertEqual(10, len(self.catalog._catalog_index))

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "new")

        solution = Solution(d)

        # call
        self.catalog.remove(solution)

        # assert
        self.assertIn("Solution not installed!", self.get_logs()[-1])
        self.assertEqual(10, len(self.catalog._catalog_index))

    def test_remove_not_local(self):
        # prepare
        self.populate_index()
        self.assertEqual(10, len(self.catalog._catalog_index))

        d = {}
        for key in CatalogIndex.get_solution_column_keys():
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)
        self.catalog.is_local = MagicMock(return_value=False)

        # call
        self.catalog.remove(solution)

        # assert
        self.assertIn("Cannot remove entries", self.get_logs()[-1])
        self.assertEqual(10, len(self.catalog._catalog_index))

    def test_download_index_files(self):
        dir = Path(self.tmp_dir.name).joinpath('bla')
        db, meta = retrieve_index_files_from_src(DefaultValues.default_catalog_src.value, dir)
        self.assertTrue(db.exists())
        self.assertTrue(meta.exists())
        force_remove(dir)

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
        with self.catalog.retrieve_catalog(dl_path, force_retrieve=True) as repo:
            # assert
            self.assertIsNotNone(repo)

        self.assertFalse(blocking_file.exists())
        self.assertTrue(dl_path.stat().st_size > 0)

    def test_get_meta_information(self):
        self.assertEqual(
            self.catalog.get_meta_information(),
            self.get_catalog_meta_dict(self.catalog._name, self.catalog._version, self.catalog._type)
        )


if __name__ == '__main__':
    unittest.main()
