import unittest.mock
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.resolve_operations import get_doi_from_input, get_cgnv_from_input, get_gnv_from_input, \
    get_attributes_from_string, check_file_or_url, dict_to_coordinates, get_zip_name_prefix, get_zip_name, \
    solution_to_coordinates, check_doi, parse_doi_service_url, _parse_zenodo_url
from test.unit.test_unit_common import TestUnitCommon


class TestResolveOperations(TestUnitCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_get_doi_from_input(self):
        solution = {
            "doi": "prefix/suffix",
        }
        self.assertEqual(solution, get_doi_from_input("doi:prefix/suffix"))
        self.assertEqual(solution, get_doi_from_input("prefix/suffix"))
        self.assertIsNone(get_doi_from_input("prefixOnly"))
        self.assertIsNone(get_doi_from_input("doi:"))
        self.assertIsNone(get_doi_from_input(":"))
        self.assertIsNone(get_doi_from_input("grp:name:version"))

    @unittest.skip("Needs to be implemented!")
    def test_is_pathname_valid(self):
        pass

    def test_get_cgnv_from_input(self):
        solution = {
            "catalog": "catalog",
            "group": "grp",
            "name": "name",
            "version": "version"
        }
        self.assertEqual(solution, get_cgnv_from_input("catalog:grp:name:version"))

    def test_get_gnv_from_input(self):
        solution = {
            "group": "grp",
            "name": "name",
            "version": "version"
        }

        self.assertEqual(solution, get_gnv_from_input("grp:name:version"))
        self.assertIsNone(get_gnv_from_input("grp:name"))
        self.assertIsNone(get_gnv_from_input("grp:version"))
        self.assertIsNone(get_gnv_from_input("grp:name:version:uselessInput"))
        self.assertIsNone(get_gnv_from_input("uselessInput"))
        self.assertIsNone(get_gnv_from_input("::"))
        self.assertIsNone(get_gnv_from_input("doi:prefix/suffix"))

    @patch('album.core.utils.operations.resolve_operations.get_doi_from_input')
    @patch('album.core.utils.operations.resolve_operations.get_gnv_from_input')
    def test_get_attributes_from_string_gnv_input(self, get_gnv_from_input_mock, get_doi_from_input_mock):
        # mocks
        get_gnv_from_input_mock.return_value = "gnv"
        get_doi_from_input_mock.return_value = None

        r = get_attributes_from_string("gnv_input")

        self.assertEqual("gnv", r)

        get_doi_from_input_mock.assert_called_once()
        get_gnv_from_input_mock.assert_called_once()

    @patch('album.core.utils.operations.resolve_operations.get_doi_from_input')
    @patch('album.core.utils.operations.resolve_operations.get_gnv_from_input')
    def test_get_attributes_from_string_doi_input(self, get_gnv_from_input_mock, get_doi_from_input_mock):
        # mocks
        get_doi_from_input_mock.return_value = "doi"
        get_gnv_from_input_mock.return_value = None

        r = get_attributes_from_string("doi_input")

        self.assertEqual("doi", r)
        get_doi_from_input_mock.assert_called_once()
        get_gnv_from_input_mock.assert_not_called()

    @patch('album.core.utils.operations.resolve_operations.get_doi_from_input')
    @patch('album.core.utils.operations.resolve_operations.get_gnv_from_input')
    def test_get_attributes_from_string_wrong_input(self, get_gnv_from_input_mock, get_doi_from_input_mock):
        # mocks
        get_doi_from_input_mock.return_value = None
        get_gnv_from_input_mock.return_value = None

        with self.assertRaises(ValueError):
            get_attributes_from_string("aVeryStupidInput")

        get_doi_from_input_mock.assert_called_once()
        get_gnv_from_input_mock.assert_called_once()

    @patch('album.core.utils.operations.resolve_operations.prepare_path')
    @patch('album.core.utils.operations.resolve_operations.download_resource')
    @patch('album.core.utils.operations.resolve_operations.parse_doi_service_url')
    @patch('album.core.utils.operations.resolve_operations.retrieve_redirect_url')
    def test_check_doi(self, retrieve_url_mock, parse_doi_mock, dl_mock, prepare_mock):
        # prepare
        doi = "10.5281/zenodo.5571504"
        # mocks
        retrieve_url_mock.return_value = "https://zenodo.org/record/5571504"
        parse_doi_mock.return_value = 'https://zenodo.org/api/files/07e481f6-30bf-40ed-88f2-3f71fa537056/solution.zip'
        dl_mock.return_value = "myDownloadFile"
        prepare_mock.return_value = "whatever"

        # call
        check_doi(doi, "myTempDir")

        # assert
        retrieve_url_mock.assert_called_once_with("https://doi.org/10.5281/zenodo.5571504")
        parse_doi_mock.assert_called_once_with(retrieve_url_mock.return_value)
        dl_mock.assert_called_once_with(parse_doi_mock.return_value, "myTempDir")
        prepare_mock.assert_called_once_with("myDownloadFile", "myTempDir")

    @patch('album.core.utils.operations.resolve_operations._parse_zenodo_url', return_value="link")
    def test_parse_doi_service_url(self, _):
        # prepare
        url1 = "https://zenodo.org/record/5571504"
        url2 = "https://zenod.org/record/5571504"
        url3 = "https://subdomain.zenodo.org/record/5571504"
        url4 = "https://bullshit.net/"
        url5 = "https://zenodo.org"

        # calls no error
        parse_doi_service_url(url1)
        parse_doi_service_url(url3)

        # calls expect error
        with self.assertRaises(NotImplementedError):
            parse_doi_service_url(url2)
        with self.assertRaises(NotImplementedError):
            parse_doi_service_url(url4)
        with self.assertRaises(NotImplementedError):
            parse_doi_service_url(url5)

    @patch('album.core.utils.operations.resolve_operations.retrieve_zenodo_record_download_zip')
    def test__parse_zenodo_url(self, rzrdz):
        # prepare
        url1 = "https://zenodo.org/record/5571504"
        url2 = "https://zenod.org/record/5571504"
        url3 = "https://subdomain.zenodo.org/recordd/5571504"
        url4 = "https://bullshitt/record/5571504"
        url5 = "https://zenodo.org/whatsoever/5571504"
        url6 = "https://zenodo.org/record/5571504/1234"

        # call
        _parse_zenodo_url(url1)

        # assert
        rzrdz.assert_called_once_with("5571504")

        # call expect error
        with self.assertRaises(ValueError):
            _parse_zenodo_url(url2)
        with self.assertRaises(ValueError):
            _parse_zenodo_url(url3)
        with self.assertRaises(ValueError):
            _parse_zenodo_url(url4)
        with self.assertRaises(ValueError):
            _parse_zenodo_url(url5)
        with self.assertRaises(ValueError):
            _parse_zenodo_url(url6)

    @unittest.skip("Needs to be implemented!")
    def test_retrieve_zenodo_record_download_zip(self):
        # todo: implement
        pass

    @patch('album.core.utils.operations.resolve_operations.check_zip')
    @patch('album.core.utils.operations.resolve_operations.rand_folder_name')
    @patch('album.core.utils.operations.resolve_operations.copy_folder')
    @patch('album.core.utils.operations.resolve_operations.copy')
    @patch('album.core.utils.operations.resolve_operations.unzip_archive')
    @patch('album.core.utils.operations.resolve_operations.download')
    def test_check_file_or_url_case_url(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
                                        rand_folder_name_mock, check_zip_mock):
        # prepare
        zipfile = Path(self.tmp_dir.name).joinpath("zipfile.zip")
        zipfile.touch()

        pythonfile = Path(self.tmp_dir.name).joinpath("pythonfile.py")
        pythonfile.touch()

        # mocks
        download_mock.return_value = pythonfile
        unzip_archive_mock.return_value = Path("uPath")
        copy_mock.return_value = Path("cPath")
        copy_folder_mock.return_value = Path("cfPath")
        rand_folder_name_mock.return_value = Path("rPath")
        check_zip_mock.return_value = True

        # case URL
        case_url = check_file_or_url("http://test.de",
                                     Path(self.tmp_dir.name).joinpath(DefaultValues.cache_path_tmp_prefix.value))
        self.assertEqual(copy_mock.return_value, case_url)
        download_mock.assert_called_once()
        rand_folder_name_mock.assert_called_once()
        copy_mock.assert_called_once()

        copy_folder_mock.assert_not_called()
        unzip_archive_mock.assert_not_called()
        check_zip_mock.assert_not_called()

    @patch('album.core.utils.operations.resolve_operations.check_zip')
    @patch('album.core.utils.operations.resolve_operations.rand_folder_name')
    @patch('album.core.utils.operations.resolve_operations.copy_folder')
    @patch('album.core.utils.operations.resolve_operations.copy')
    @patch('album.core.utils.operations.resolve_operations.unzip_archive')
    @patch('album.core.utils.operations.resolve_operations.download')
    def test_check_file_or_url_case_zip(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
                                        rand_folder_name_mock, check_zip_mock):
        # prepare
        zipfile = Path(self.tmp_dir.name).joinpath("zipfile.zip")
        zipfile.touch()

        pythonfile = Path(self.tmp_dir.name).joinpath("pythonfile.py")
        pythonfile.touch()

        # mocks
        download_mock.return_value = pythonfile
        unzip_archive_mock.return_value = Path("uPath")
        copy_mock.return_value = Path("cPath")
        copy_folder_mock.return_value = Path("cfPath")
        rand_folder_name_mock.return_value = Path("rPath")
        check_zip_mock.return_value = True

        # case zip
        case_zip = check_file_or_url(str(zipfile),
                                     Path(self.tmp_dir.name).joinpath(DefaultValues.cache_path_tmp_prefix.value))
        self.assertEqual(unzip_archive_mock.return_value.joinpath("solution.py"), case_zip)

        unzip_archive_mock.assert_called_once_with(
            zipfile, Path(self.tmp_dir.name).joinpath("tmp", rand_folder_name_mock.return_value)
        )
        rand_folder_name_mock.assert_called_once()
        check_zip_mock.assert_called_once_with(zipfile)

        copy_mock.assert_not_called()
        download_mock.assert_not_called()
        copy_folder_mock.assert_not_called()

    @patch('album.core.utils.operations.resolve_operations.check_zip')
    @patch('album.core.utils.operations.resolve_operations.rand_folder_name')
    @patch('album.core.utils.operations.resolve_operations.copy_folder')
    @patch('album.core.utils.operations.resolve_operations.copy')
    @patch('album.core.utils.operations.resolve_operations.unzip_archive')
    @patch('album.core.utils.operations.resolve_operations.download')
    def test_check_file_or_url_case_file(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
                                         rand_folder_name_mock, check_zip_mock):
        # prepare
        zipfile = Path(self.tmp_dir.name).joinpath("zipfile.zip")
        zipfile.touch()

        pythonfile = Path(self.tmp_dir.name).joinpath("pythonfile.py")
        pythonfile.touch()

        # mocks
        download_mock.return_value = pythonfile
        unzip_archive_mock.return_value = Path("uPath")
        copy_mock.return_value = Path("cPath")
        copy_folder_mock.return_value = Path("cfPath")
        rand_folder_name_mock.return_value = Path("rPath")
        check_zip_mock.return_value = True

        # case file
        case_file = check_file_or_url(str(pythonfile),
                                      Path(self.tmp_dir.name).joinpath(DefaultValues.cache_path_tmp_prefix.value))
        self.assertEqual(copy_mock.return_value, case_file)

        copy_mock.assert_called_once_with(
            pythonfile, Path(self.tmp_dir.name).joinpath("tmp", rand_folder_name_mock.return_value, "solution.py")
        )
        rand_folder_name_mock.assert_called_once()

        unzip_archive_mock.assert_not_called()
        download_mock.assert_not_called()
        copy_folder_mock.assert_not_called()
        check_zip_mock.assert_not_called()

    @patch('album.core.utils.operations.resolve_operations.check_zip')
    @patch('album.core.utils.operations.resolve_operations.rand_folder_name')
    @patch('album.core.utils.operations.resolve_operations.copy_folder')
    @patch('album.core.utils.operations.resolve_operations.copy')
    @patch('album.core.utils.operations.resolve_operations.unzip_archive')
    @patch('album.core.utils.operations.resolve_operations.download')
    def test_check_file_or_url_case_folder(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
                                           rand_folder_name_mock, check_zip_mock):
        # prepare
        zipfile = Path(self.tmp_dir.name).joinpath("zipfile.zip")
        zipfile.touch()

        pythonfile = Path(self.tmp_dir.name).joinpath("pythonfile.py")
        pythonfile.touch()

        # mocks
        download_mock.return_value = pythonfile
        unzip_archive_mock.return_value = Path("uPath")
        copy_mock.return_value = Path("cPath")
        copy_folder_mock.return_value = Path("cfPath")
        rand_folder_name_mock.return_value = Path("rPath")
        check_zip_mock.return_value = True

        # case file
        case_folder = check_file_or_url(self.tmp_dir.name,
                                        Path(self.tmp_dir.name).joinpath(DefaultValues.cache_path_tmp_prefix.value))
        self.assertEqual(copy_folder_mock.return_value.joinpath("solution.py"), case_folder)

        copy_folder_mock.assert_called_once_with(
            Path(self.tmp_dir.name),
            Path(self.tmp_dir.name).joinpath("tmp", rand_folder_name_mock.return_value),
            copy_root_folder=False
        )
        rand_folder_name_mock.assert_called_once()

        unzip_archive_mock.assert_not_called()
        download_mock.assert_not_called()
        copy_mock.assert_not_called()
        check_zip_mock.assert_not_called()

    def test_dict_to_coordinates(self):
        self.assertEqual(Coordinates(self.solution_default_dict["group"], self.solution_default_dict["name"],
                                     self.solution_default_dict["version"]),
                         dict_to_coordinates(self.solution_default_dict))
        sol_dict = deepcopy(self.solution_default_dict)
        sol_dict.pop("version")
        with self.assertRaises(ValueError):
            self.assertTrue(dict_to_coordinates(sol_dict))

    def test_solution_to_coordinates(self):
        self.create_test_solution_no_env()
        self.assertEqual(Coordinates("tsg", "tsn", "tsv"), solution_to_coordinates(self.active_solution))

    @patch('album.core.utils.operations.resolve_operations.get_zip_name_prefix', return_value="asd")
    def test_get_zip_name(self, _):
        self.assertEqual("asd.zip", get_zip_name(Coordinates("g", "n", "v")))

    def test_get_zip_name_prefix(self):
        self.assertEqual("g_n_v", get_zip_name_prefix(Coordinates("g", "n", "v")))


if __name__ == '__main__':
    unittest.main()
