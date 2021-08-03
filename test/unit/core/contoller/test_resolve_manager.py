from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.controller.resolve_manager import ResolveManager
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestResolveManager(TestUnitCommon):
    def setUp(self):
        super().setUp()
        self.create_test_config()
        self.create_test_solution_no_env()

        self.resolve_manager = ResolveManager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_resolve_installed_and_load_valid_path(self):
        # mocks
        _check_file_or_url = MagicMock(return_value="aValidPath")
        self.resolve_manager._check_file_or_url = _check_file_or_url

        _resolve_local_file = MagicMock(return_value=None)
        self.resolve_manager._resolve_local_file = _resolve_local_file

        _resolve_from_catalog = MagicMock(return_value=None)
        self.resolve_manager._resolve_from_catalog = _resolve_from_catalog

        # call
        self.resolve_manager.resolve_installed_and_load("myPathToAFileOrAUrl")

        # assert
        _check_file_or_url.assert_called_once_with("myPathToAFileOrAUrl")
        _resolve_local_file.assert_called_once_with("aValidPath")
        _resolve_from_catalog.assert_not_called()

    def test_resolve_installed_and_load_grp_name_version(self):
        # mocks
        _check_file_or_url = MagicMock(return_value=None)
        self.resolve_manager._check_file_or_url = _check_file_or_url

        _resolve_local_file = MagicMock(return_value=None)
        self.resolve_manager._resolve_local_file = _resolve_local_file

        _resolve_from_catalog = MagicMock(return_value=None)
        self.resolve_manager._resolve_from_catalog = _resolve_from_catalog

        # call
        self.resolve_manager.resolve_installed_and_load("grp:name:version")

        # assert
        _check_file_or_url.assert_called_once_with("grp:name:version")
        _resolve_local_file.assert_not_called()
        _resolve_from_catalog.assert_called_once_with("grp:name:version")

    @patch('album.core.controller.resolve_manager.load')
    def test_resolve_and_load_valid_local_input(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        _check_file_or_url = MagicMock(return_value="copiedFilePath")
        self.resolve_manager._check_file_or_url = _check_file_or_url

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        get_attributes_from_string = MagicMock(return_value=None)
        self.resolve_manager.get_attributes_from_string = get_attributes_from_string

        # call
        r = self.resolve_manager.resolve_and_load("pathToAValidFile")

        expected = [
            {"path": "copiedFilePath", "catalog": self.test_catalog_manager.local_catalog},
            self.active_solution
        ]

        # assert
        self.assertEqual(expected, r)

        _check_file_or_url.assert_called_once_with("pathToAValidFile")  # check local input
        set_environment.assert_called_once_with(self.test_catalog_manager.local_catalog.id)  # use correct catalog
        load_mock.assert_called_once_with("copiedFilePath")  # load with correct path
        get_attributes_from_string.assert_not_called()  # do not go into remote

    @patch('album.core.controller.resolve_manager.load')
    def test_resolve_and_load_remote_input(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        _check_file_or_url = MagicMock(return_value=None)
        self.resolve_manager._check_file_or_url = _check_file_or_url

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        get_attributes_from_string = MagicMock(return_value="attrs_object")
        self.resolve_manager.get_attributes_from_string = get_attributes_from_string

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        resolve = MagicMock(return_value={"path": "aValidPath", "catalog": _catalog})
        self.test_catalog_manager.resolve = resolve

        # call
        r = self.resolve_manager.resolve_and_load("grp:name:version")

        expected = [
            {"path": "aValidPath", "catalog": _catalog},
            self.active_solution
        ]

        # assert
        self.assertEqual(expected, r)

        _check_file_or_url.assert_called_once_with("grp:name:version")  # locally checked
        get_attributes_from_string.assert_called_once_with("grp:name:version")  # extract attrs-dict from input
        resolve.assert_called_once_with("attrs_object")  # resolve with correct attrs-dict
        load_mock.assert_called_once_with("aValidPath")  # load with the resolved path
        set_environment.assert_called_once_with(_catalog.id)  # set environment with correct id

    @patch('album.core.controller.resolve_manager.load')
    def test_resolve_dependency_and_load(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=[{"catalog_id": "aNiceId"}])
        self.resolve_manager.solution_db.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        resolve_directly = MagicMock(return_value={"path": "aValidPath", "catalog": _catalog})
        self.test_catalog_manager.resolve_directly = resolve_directly

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        expected = [resolve_directly.return_value, self.active_solution]
        r = self.resolve_manager.resolve_dependency_and_load({"group": "g", "name": "n", "version": "v"})

        self.assertEqual(expected, r)

        get_solutions_by_grp_name_version.assert_called_once_with("g", "n", "v")
        resolve_directly.assert_called_once_with("aNiceId", "g", "n", "v")
        load_mock.assert_called_once_with("aValidPath")
        set_environment.assert_called_once_with(_catalog.id)

    @patch('album.core.controller.resolve_manager.load')
    def test_resolve_dependency_and_load_error(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=None)
        self.resolve_manager.solution_db.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        resolve_directly = MagicMock(return_value=None)
        self.test_catalog_manager.resolve_directly = resolve_directly

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        with self.assertRaises(LookupError):
            self.resolve_manager.resolve_dependency_and_load({"group": "g", "name": "n", "version": "v"})

        get_solutions_by_grp_name_version.assert_called_once_with("g", "n", "v")
        resolve_directly.assert_not_called()
        load_mock.assert_not_called()
        set_environment.assert_not_called()

    @patch('album.core.controller.resolve_manager.check_zip')
    @patch('album.core.controller.resolve_manager.rand_folder_name')
    @patch('album.core.controller.resolve_manager.copy_folder')
    @patch('album.core.controller.resolve_manager.copy')
    @patch('album.core.controller.resolve_manager.unzip_archive')
    @patch('album.core.controller.resolve_manager.download')
    def test__check_file_or_url_case_url(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
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
        case_url = self.resolve_manager._check_file_or_url("http://test.de")
        self.assertEqual(copy_mock.return_value, case_url)
        download_mock.assert_called_once()
        rand_folder_name_mock.assert_called_once()
        copy_mock.assert_called_once()

        copy_folder_mock.assert_not_called()
        unzip_archive_mock.assert_not_called()
        check_zip_mock.assert_not_called()

    @patch('album.core.controller.resolve_manager.check_zip')
    @patch('album.core.controller.resolve_manager.rand_folder_name')
    @patch('album.core.controller.resolve_manager.copy_folder')
    @patch('album.core.controller.resolve_manager.copy')
    @patch('album.core.controller.resolve_manager.unzip_archive')
    @patch('album.core.controller.resolve_manager.download')
    def test__check_file_or_url_case_zip(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
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
        case_zip = self.resolve_manager._check_file_or_url(str(zipfile))
        self.assertEqual(unzip_archive_mock.return_value.joinpath("solution.py"), case_zip)

        unzip_archive_mock.assert_called_once_with(
            zipfile, Path(self.tmp_dir.name).joinpath("tmp", rand_folder_name_mock.return_value)
        )
        rand_folder_name_mock.assert_called_once()
        check_zip_mock.assert_called_once_with(zipfile)

        copy_mock.assert_not_called()
        download_mock.assert_not_called()
        copy_folder_mock.assert_not_called()

    @patch('album.core.controller.resolve_manager.check_zip')
    @patch('album.core.controller.resolve_manager.rand_folder_name')
    @patch('album.core.controller.resolve_manager.copy_folder')
    @patch('album.core.controller.resolve_manager.copy')
    @patch('album.core.controller.resolve_manager.unzip_archive')
    @patch('album.core.controller.resolve_manager.download')
    def test__check_file_or_url_case_file(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
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
        case_file = self.resolve_manager._check_file_or_url(str(pythonfile))
        self.assertEqual(copy_mock.return_value, case_file)

        copy_mock.assert_called_once_with(
            pythonfile, Path(self.tmp_dir.name).joinpath("tmp", rand_folder_name_mock.return_value, "solution.py")
        )
        rand_folder_name_mock.assert_called_once()

        unzip_archive_mock.assert_not_called()
        download_mock.assert_not_called()
        copy_folder_mock.assert_not_called()
        check_zip_mock.assert_not_called()

    @patch('album.core.controller.resolve_manager.check_zip')
    @patch('album.core.controller.resolve_manager.rand_folder_name')
    @patch('album.core.controller.resolve_manager.copy_folder')
    @patch('album.core.controller.resolve_manager.copy')
    @patch('album.core.controller.resolve_manager.unzip_archive')
    @patch('album.core.controller.resolve_manager.download')
    def test__check_file_or_url_case_folder(self, download_mock, unzip_archive_mock, copy_mock, copy_folder_mock,
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
        case_folder = self.resolve_manager._check_file_or_url(self.tmp_dir.name)
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

    @patch('album.core.controller.resolve_manager.load')
    def test__resolve_from_catalog(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_attributes_from_string = MagicMock(return_value={"group": "g", "name": "n", "version": "v"})
        self.resolve_manager.get_attributes_from_string = get_attributes_from_string

        get_solutions_by_grp_name_version = MagicMock(return_value=[{"catalog_id": "aNiceId"}])
        self.resolve_manager.solution_db.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        resolve_directly = MagicMock(return_value={"path": "aValidPath", "catalog": _catalog})
        self.test_catalog_manager.resolve_directly = resolve_directly

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        r = self.resolve_manager._resolve_from_catalog("grp:name:version")

        expected = [
            {"path": "aValidPath", "catalog": _catalog},
            self.active_solution
        ]

        # assert
        self.assertEqual(expected, r)

        get_attributes_from_string.assert_called_once_with("grp:name:version")
        get_solutions_by_grp_name_version.assert_called_once_with("g", "n", "v")
        resolve_directly.assert_called_once_with("aNiceId", "g", "n", "v")
        load_mock.assert_called_once_with("aValidPath")
        set_environment.assert_called_once_with("aNiceId")

    @patch('album.core.controller.resolve_manager.load')
    def test__resolve_from_catalog_not_installed(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_attributes_from_string = MagicMock(return_value={"group": "g", "name": "n", "version": "v"})
        self.resolve_manager.get_attributes_from_string = get_attributes_from_string

        get_solutions_by_grp_name_version = MagicMock(return_value=None)
        self.resolve_manager.solution_db.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        resolve_directly = MagicMock(return_value=None)
        self.test_catalog_manager.resolve_directly = resolve_directly

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call and assert
        with self.assertRaises(LookupError):
            self.resolve_manager._resolve_from_catalog("grp:name:version")

        get_attributes_from_string.assert_called_once_with("grp:name:version")
        get_solutions_by_grp_name_version.assert_called_once_with("g", "n", "v")

        resolve_directly.assert_not_called()
        load_mock.assert_not_called()
        set_environment.assert_not_called()

    @patch('album.core.controller.resolve_manager.load')
    def test__resolve_local_file(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        _catalog = EmptyTestClass()
        _catalog.id = "aNiceId"

        get_solutions_by_grp_name_version = MagicMock(return_value=[{"catalog_id": "aNiceId"}])
        self.resolve_manager.solution_db.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        get_catalog_by_id = MagicMock(return_value=_catalog)
        self.test_catalog_manager.get_catalog_by_id = get_catalog_by_id

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        expected = [
            {
                "path": "aPath",
                "catalog": _catalog
            },
            self.active_solution
        ]

        r = self.resolve_manager._resolve_local_file("aPath")

        self.assertEqual(expected, r)

        load_mock.assert_called_once_with("aPath")
        get_solutions_by_grp_name_version.assert_called_once_with("tsg", "tsn", "tsv")
        get_catalog_by_id.assert_called_once_with("aNiceId")
        set_environment.assert_called_once_with("aNiceId")

    @patch('album.core.controller.resolve_manager.load')
    def test__resolve_local_file_invalid(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_solutions_by_grp_name_version = MagicMock(return_value=None)
        self.resolve_manager.solution_db.get_solutions_by_grp_name_version = get_solutions_by_grp_name_version

        get_catalog_by_id = MagicMock(return_value=None)
        self.test_catalog_manager.get_catalog_by_id = get_catalog_by_id

        set_environment = MagicMock(return_value=None)
        self.active_solution.set_environment = set_environment

        # call
        with self.assertRaises(LookupError):
            self.resolve_manager._resolve_local_file("aPath")

        load_mock.assert_called_once_with("aPath")
        get_solutions_by_grp_name_version.assert_called_once_with("tsg", "tsn", "tsv")
        get_catalog_by_id.assert_not_called()
        set_environment.assert_not_called()

    def test_get_attributes_from_string_wrong_input(self):
        # mocks
        get_doi_from_input = MagicMock(return_value=None)
        get_gnv_from_input = MagicMock(return_value=None)
        resolve_dependency = MagicMock(return_value=None)

        self.resolve_manager.get_doi_from_input = get_doi_from_input
        self.resolve_manager.get_gnv_from_input = get_gnv_from_input
        self.resolve_manager.resolve_dependency = resolve_dependency

        with self.assertRaises(ValueError):
            self.resolve_manager.get_attributes_from_string("aVeryStupidInput")

        get_doi_from_input.assert_called_once()
        get_gnv_from_input.assert_called_once()
        resolve_dependency.assert_not_called()

    def test_get_attributes_from_string_doi_input(self):
        # mocks
        get_doi_from_input = MagicMock(return_value="doi")
        get_gnv_from_input = MagicMock(return_value=None)

        self.resolve_manager.get_doi_from_input = get_doi_from_input
        self.resolve_manager.get_gnv_from_input = get_gnv_from_input

        r = self.resolve_manager.get_attributes_from_string("doi_input")

        self.assertEqual("doi", r)
        get_doi_from_input.assert_called_once()
        get_gnv_from_input.assert_not_called()

    def test_get_attributes_from_string_gnv_input(self):
        # mocks
        get_doi_from_input = MagicMock(return_value=None)
        get_gnv_from_input = MagicMock(return_value="gnv")

        self.resolve_manager.get_doi_from_input = get_doi_from_input
        self.resolve_manager.get_gnv_from_input = get_gnv_from_input

        r = self.resolve_manager.get_attributes_from_string("gnv_input")

        self.assertEqual("gnv", r)

        get_doi_from_input.assert_called_once()
        get_gnv_from_input.assert_called_once()

    def test_get_gnv_from_input(self):
        solution = {
            "group": "grp",
            "name": "name",
            "version": "version"
        }

        self.assertEqual(solution, self.resolve_manager.get_gnv_from_input("grp:name:version"))
        self.assertIsNone(self.resolve_manager.get_gnv_from_input("grp:name"))
        self.assertIsNone(self.resolve_manager.get_gnv_from_input("grp:version"))
        self.assertIsNone(self.resolve_manager.get_gnv_from_input("grp:name:version:uselessInput"))
        self.assertIsNone(self.resolve_manager.get_gnv_from_input("uselessInput"))
        self.assertIsNone(self.resolve_manager.get_gnv_from_input("::"))
        self.assertIsNone(self.resolve_manager.get_gnv_from_input("doi:prefix/suffix"))

    def test_get_cgnv_from_input(self):
        solution = {
            "catalog": "catalog",
            "group": "grp",
            "name": "name",
            "version": "version"
        }
        self.assertEqual(solution, self.resolve_manager.get_cgnv_from_input("catalog:grp:name:version"))

    def test_get_doi_from_input(self):
        solution = {
            "doi": "prefix/suffix",
        }
        self.assertEqual(solution, self.resolve_manager.get_doi_from_input("doi:prefix/suffix"))
        self.assertEqual(solution, self.resolve_manager.get_doi_from_input("prefix/suffix"))
        self.assertIsNone(self.resolve_manager.get_doi_from_input("prefixOnly"))
        self.assertIsNone(self.resolve_manager.get_doi_from_input("doi:"))
        self.assertIsNone(self.resolve_manager.get_doi_from_input(":"))
        self.assertIsNone(self.resolve_manager.get_doi_from_input("grp:name:version"))
