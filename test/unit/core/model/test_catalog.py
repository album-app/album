import os
import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.configuration import Configuration
from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.core.model.solution import Solution
from test.unit.test_unit_common import TestUnitCommon


class TestCatalog(TestUnitCommon):

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
        Configuration().setup(
            base_cache_path=Path(self.tmp_dir.name).joinpath("album")
        )
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        CatalogHandler.create_new_catalog(catalog_src, "test")
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        self.catalog = Catalog(0, "test", src=catalog_src, path=catalog_path)
        MigrationManager().load_index(self.catalog)

    def tearDown(self) -> None:
        self.catalog.dispose()
        super().tearDown()

    def test__init__(self):
        new_catalog = self.catalog
        self.assertEqual(new_catalog.path, Path(self.tmp_dir.name).joinpath("testPath"))
        self.assertIsNotNone(new_catalog.src)
        self.assertTrue(new_catalog.is_local())
        self.assertEqual(new_catalog.name, "test")
        self.assertEqual(str(new_catalog.get_meta_information()), "{\'name\': \'test\', \'version\': \'0.1.0\'}")

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
        # prepare
        self.populate_index()
        get_solution_file_mock.side_effect = [Path(self.closed_tmp_file.name)]

        # call
        search_result = self.catalog.resolve(Coordinates("group0", "name0", "version0"))

        # assert
        self.assertEqual(search_result, Path(self.closed_tmp_file.name))

    def test_resolve_doi(self):
        # prepare
        self.catalog.catalog_index.get_solution_by_doi = MagicMock(
            return_value={"path": self.closed_tmp_file.name, "group": "group0", "name": "name0", "version": "version0"})

        # call
        search_result = self.catalog.resolve_doi("doi0")

        # assert
        self.assertEqual(Path(self.catalog.path).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "group0", "name0", "version0", DefaultValues.solution_default_name.value), search_result)

    def test_get_solution_path(self):
        # call
        self.assertEqual(
            self.catalog.get_solution_path(Coordinates("g", "n", "v")),
            self.catalog.path.joinpath(self.catalog.gnv_solution_prefix, "g", "n", "v")
        )

    def test_get_solution_file(self):
        res = self.catalog.path.joinpath(self.catalog.gnv_solution_prefix, "g", "n", "v").joinpath("solution.py")

        # call
        self.assertEqual(res, self.catalog.get_solution_file(Coordinates("g", "n", "v")))

    def test_get_solution_zip(self):
        res = self.catalog.path.joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        # call
        self.assertEqual(res, self.catalog.get_solution_zip(Coordinates("g", "n", "v")))

    def test_get_solution_zip_suffix(self):
        res = Path("").joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        # call
        self.assertEqual(res, self.catalog.get_solution_zip_suffix(Coordinates("g", "n", "v")))

    @patch("album.core.model.catalog.download_resource", return_value=None)
    @patch("album.core.model.catalog.unzip_archive", return_value=Path("a/Path"))
    def test_retrieve_solution(self, unzip_mock, dl_mock):
        # prepare
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               "http://NonsenseUrl.git")
        self.catalog.is_cache = MagicMock(return_value=False)

        dl_url = "http://NonsenseUrl" + "/-/raw/main/solutions/g/n/v/g_n_v.zip"
        dl_path = self.catalog.path.joinpath(
            DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip"
        )
        res = Path("a/Path").joinpath(DefaultValues.solution_default_name.value)

        # call & assert
        self.assertEqual(res, self.catalog.retrieve_solution(Coordinates("g", "n", "v")))

        # assert
        dl_mock.assert_called_once_with(dl_url, dl_path)
        unzip_mock.assert_called_once_with(dl_path)

    @unittest.skip("Needs to be implemented!")
    def test_update_index_cache_if_possible(self):
        pass

    @patch('album.core.model.catalog.force_remove')
    def test_update_index_cache_remote_catalog_src_deleted(self, force_remove_mock):
        self.catalog.src = "https://mycatalog.org"
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
        self.catalog.src = "https://mycatalog.org"
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
        self.catalog.src = None  # set to cache only catalog

        # call
        self.assertFalse(self.catalog.update_index_cache())

    def test_get_version(self):
        # mocks
        get_version_mock = MagicMock(return_value="0.1.0")
        self.catalog.catalog_index.get_version = get_version_mock

        with patch('album.core.model.catalog.Catalog.retrieve_catalog_meta_information') as retrieve_c_m_i_mock:
            retrieve_c_m_i_mock.return_value = {"version": "0.1.0"}

            # call
            v = self.catalog.get_version()

            # assert
            self.assertEqual("0.1.0", v)
            retrieve_c_m_i_mock.assert_called_once_with(self.catalog.path)

    def test_get_version_wrong_meta(self):
        # mocks
        get_version_mock = MagicMock(return_value="0.1.0")  # version the database index is in
        self.catalog.catalog_index.get_version = get_version_mock

        with patch('album.core.model.catalog.Catalog.retrieve_catalog_meta_information') as retrieve_c_m_i_mock:
            retrieve_c_m_i_mock.return_value = {"version": "0.1.1"}  # version the meta file claims

            # call
            with self.assertRaises(ValueError):
                self.catalog.get_version()

            # assert
            retrieve_c_m_i_mock.assert_called_once_with(self.catalog.path)

    def test_get_version_no_meta(self):
        # mocks
        get_version_mock = MagicMock(return_value="0.1.0")  # version the database index is in
        self.catalog.catalog_index.get_version = get_version_mock

        with patch('album.core.model.catalog.Catalog.retrieve_catalog_meta_information') as retrieve_c_m_i_mock:
            retrieve_c_m_i_mock.return_value = None  # no meta info available

            # call
            with self.assertRaises(ValueError):
                self.catalog.get_version()

            # assert
            retrieve_c_m_i_mock.assert_called_once_with(self.catalog.path)

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

        # call
        with self.assertRaises(RuntimeError):
            self.catalog.add(solution)

    def test_add_solution_already_present_no_overwrite(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)

        # call
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

        # call
        self.catalog.add(solution, force_overwrite=True)

        # assert
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_remove(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)
        # call
        self.catalog.remove(solution)

        # assert
        self.assertEqual(len(self.catalog.catalog_index), 9)

    def test_remove_not_installed(self):
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "new")

        solution = Solution(d)

        # call
        self.catalog.remove(solution)

        # assert
        self.assertIn("WARNING - Solution not installed!", self.get_logs()[-1])
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_remove_not_local(self):
        # prepare
        self.populate_index()
        self.assertEqual(len(self.catalog.catalog_index), 10)

        d = {}
        for key in Solution.deploy_keys:
            d[key] = "%s%s" % (key, "0")

        solution = Solution(d)
        self.catalog.is_local = MagicMock(return_value=False)

        # call
        self.catalog.remove(solution)

        # assert
        self.assertIn("WARNING - Cannot remove entries", self.get_logs()[-1])
        self.assertEqual(len(self.catalog.catalog_index), 10)

    def test_copy_index_from_src_to_cache(self):
        # prepare
        self.catalog.src.joinpath("album_catalog_index.db").touch()
        self.catalog.src.joinpath("album_catalog_index.json").touch()

        Path(self.catalog.path).joinpath("album_catalog_index.db").unlink()
        Path(self.catalog.path).joinpath("album_catalog_index.json").unlink()

        self.assertFalse(Path(self.catalog.path).joinpath("album_catalog_index.db").exists())
        self.assertFalse(Path(self.catalog.path).joinpath("album_catalog_index.json").exists())

        # deliberately not mocking copy call
        self.assertTrue(self.catalog.copy_index_from_src_to_cache())

        # assert
        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.json").exists())

    def test_copy_index_from_src_to_cache_no_db(self):
        # prepare
        self.catalog.src.joinpath("album_catalog_index.json").touch()

        Path(self.catalog.path).joinpath("album_catalog_index.db").unlink()
        Path(self.catalog.path).joinpath("album_catalog_index.json").unlink()

        self.assertFalse(Path(self.catalog.path).joinpath("album_catalog_index.db").exists())
        self.assertFalse(Path(self.catalog.path).joinpath("album_catalog_index.json").exists())

        # deliberately not mocking copy call
        self.assertTrue(self.catalog.copy_index_from_src_to_cache())

        # assert
        self.assertFalse(Path(self.catalog.path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.json").exists())

    def test_copy_index_from_src_to_cache_db_deleted(self):
        # prepare
        self.catalog.src.joinpath("album_catalog_index.json").touch()

        Path(self.catalog.path).joinpath("album_catalog_index.db").touch()
        Path(self.catalog.path).joinpath("album_catalog_index.json").touch()

        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.json").exists())

        # deliberately not mocking copy call
        self.assertFalse(self.catalog.copy_index_from_src_to_cache())

        # assert
        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog.path).joinpath("album_catalog_index.json").exists())

    def test_copy_index_from_cache_to_src(self):
        # prepare
        self.catalog.index_path.touch()
        self.catalog.path.joinpath("album_solution_list.json").touch()

        self.assertFalse(Path(self.catalog.src).joinpath("album_catalog_index.db").exists())
        self.assertFalse(Path(self.catalog.src).joinpath("album_solution_list.json").exists())

        # deliberately not mocking copy call
        self.catalog.copy_index_from_cache_to_src()

        # assert
        self.assertTrue(Path(self.catalog.src).joinpath("album_catalog_index.db").exists())
        self.assertTrue(Path(self.catalog.src).joinpath("album_solution_list.json").exists())

    @unittest.skip("Needs to be implemented!")
    def test_download_index(self):
        # ToDo: implement
        pass

    def test_download_index_not_downloadable(self):
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               "http://google.com/doesNotExist.ico")

        # call
        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    def test_download_index_wrong_format(self):
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
                               "https://www.google.com/favicon.ico")

        # call
        with self.assertRaises(AssertionError):
            self.catalog.download_index()

    def test_retrieve_catalog(self):
        # prepare
        self.catalog = Catalog(self.catalog.catalog_id, self.catalog.name, self.catalog.path,
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

    @patch('album.core.model.catalog.get_dict_from_json')
    @patch('album.core.model.catalog.copy', return_value={"mymeta": "value"})
    @patch('album.core.model.catalog.get_index_url')
    @patch('album.core.model.catalog.get_index_dir')
    @patch('album.core.model.catalog.download_resource')
    def test_retrieve_catalog_meta_information_case_dir(
            self, download_resource_mock, get_index_dir_mock, get_index_url_mock, copy_mock, get_dict_mock
    ):
        # prepare
        link = self.tmp_dir.name

        file = Path(link).joinpath("album_catalog_index.json")
        file.touch()

        get_index_dir_mock.return_value = ("_", file)

        # call
        Catalog.retrieve_catalog_meta_information(link)

        # assert
        get_index_url_mock.assert_not_called()
        download_resource_mock.assert_not_called()
        get_index_dir_mock.assert_called_once_with(link)
        copy_mock.assert_called_once_with(
            file, Path(self.tmp_dir.name).joinpath("album", "downloads", 'album_catalog_index.json')
        )
        get_dict_mock.assert_called_once_with({"mymeta": "value"})

    @patch('album.core.model.catalog.get_dict_from_json')
    @patch('album.core.model.catalog.copy')
    @patch('album.core.model.catalog.get_index_url', return_value=("_", "aNewUrl"))
    @patch('album.core.model.catalog.get_index_dir')
    @patch('album.core.model.catalog.download_resource', return_value={"mymeta": "value"})
    def test_retrieve_catalog_meta_information_case_url(
            self, download_resource_mock, get_index_dir_mock, get_index_url_mock, copy_mock, get_dict_mock
    ):
        # prepare
        link = "https://mylink.com"
        # call
        Catalog.retrieve_catalog_meta_information(link)

        # assert
        get_index_url_mock.assert_called_once_with(link)
        download_resource_mock.assert_called_once_with(
            "aNewUrl", Path(self.tmp_dir.name).joinpath("album", "downloads", 'album_catalog_index.json')
        )
        get_index_dir_mock.assert_not_called()
        copy_mock.assert_not_called()
        get_dict_mock.assert_called_once_with({"mymeta": "value"})

    @patch('album.core.model.catalog.get_dict_from_json')
    @patch('album.core.model.catalog.copy')
    @patch('album.core.model.catalog.get_index_url')
    @patch('album.core.model.catalog.get_index_dir')
    @patch('album.core.model.catalog.download_resource')
    def test_retrieve_catalog_meta_information_case_file_not_found(
            self, download_resource_mock, get_index_dir_mock, get_index_url_mock, copy_mock, get_dict_mock
    ):
        # prepare
        link = self.tmp_dir.name
        file = Path(link).joinpath("album_catalog_index.json")  # file does not exist

        get_index_dir_mock.return_value = ("_", file)

        # call
        with self.assertRaises(FileNotFoundError):
            Catalog.retrieve_catalog_meta_information(link)

        # assert
        get_index_url_mock.assert_not_called()
        download_resource_mock.assert_not_called()
        get_index_dir_mock.assert_called_once_with(link)
        copy_mock.assert_not_called()
        get_dict_mock.assert_not_called()

    @patch('album.core.model.catalog.get_dict_from_json')
    @patch('album.core.model.catalog.copy')
    @patch('album.core.model.catalog.get_index_url')
    @patch('album.core.model.catalog.get_index_dir')
    @patch('album.core.model.catalog.download_resource')
    def test_retrieve_catalog_meta_information_case_path_invalid(
            self, download_resource_mock, get_index_dir_mock, get_index_url_mock, copy_mock, get_dict_mock
    ):
        # prepare
        link = "mywrongpath"
        # call
        with self.assertRaises(RuntimeError):
            Catalog.retrieve_catalog_meta_information(link)

        # assert
        get_index_url_mock.assert_not_called()
        download_resource_mock.assert_not_called()
        get_index_dir_mock.assert_not_called()
        copy_mock.assert_not_called()
        get_dict_mock.assert_not_called()

    @patch('album.core.model.catalog.write_dict_to_json')
    def test_write_catalog_meta_information(self, write_dict_to_json_mock):
        self.catalog.write_catalog_meta_information()

        write_dict_to_json_mock.assert_called_once_with(
            self.catalog.path.joinpath("album_catalog_index.json"),
            {"name": self.catalog.name, "version": self.catalog.version}
        )

    def test_get_meta_information(self):
        self.assertEqual(
            self.catalog.get_meta_information(),
            {"name": self.catalog.name, "version": self.catalog.version}
        )


if __name__ == '__main__':
    unittest.main()
