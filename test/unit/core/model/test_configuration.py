import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.model.configuration import Configuration, DefaultValues
from test.unit.test_unit_common import TestUnitCommon


class TestConfiguration(TestUnitCommon):

    def setUp(self) -> None:
        super().setUp()
        self.conf = Configuration()
        self.conf.setup(base_cache_path=Path(self.tmp_dir.name).joinpath("album"),
                        configuration_file_path=self.tmp_dir.name)

    def tearDown(self) -> None:
        super().tearDown()

    def test_base_cache_path(self):
        new_tmp_dir = tempfile.TemporaryDirectory(dir=self.tmp_dir.name)

        # set
        self.conf.base_cache_path = new_tmp_dir.name

        # assert
        self.assertEqual(
            self.conf.base_cache_path,
            Path(new_tmp_dir.name)
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_solution_prefix.value),
            self.conf.cache_path_solution
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_app_prefix.value),
            self.conf.cache_path_app
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_download_prefix.value),
            self.conf.cache_path_download
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_tmp_prefix.value),
            self.conf.cache_path_tmp
        )

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windoofs")
    def test__build_conda_executable_windows(self):
        r = self.conf._build_conda_executable("myPathToConda")

        expected = Path("myPathToConda").joinpath("Scripts", "conda.exe")
        self.assertEqual(r, str(expected))

    @unittest.skipUnless(sys.platform == 'linux' or sys.platform == 'darwin', "requires a proper OS")
    def test__build_conda_executable_linux(self):
        r = self.conf._build_conda_executable("myPathToConda")

        expected = Path("myPathToConda").joinpath("bin", "conda")
        self.assertEqual(r, str(expected))

    def test_extract_catalog_name(self):
        catalog_name = "https://gitlab.com/album-app/capture-knowledge.ext"

        self.assertEqual(self.conf.extract_catalog_name(catalog_name), "capture-knowledge")

    def test_get_default_configuration(self):
        # mocks
        get_default_catalog_configuration = MagicMock(return_value="myNiceDefaultCatalogConfiguration")
        self.conf.get_default_catalog_configuration = get_default_catalog_configuration

        # call
        r = self.conf.get_default_configuration()

        self.assertEqual({"catalogs": "myNiceDefaultCatalogConfiguration"}, r)
        get_default_catalog_configuration.assert_called_once()

    def test_get_default_catalog_configuration(self):
        # mocks
        get_cache_path_catalog = MagicMock(return_value="myLocalCatalogCachePath")
        self.conf.get_cache_path_catalog = get_cache_path_catalog

        # call
        r = self.conf.get_default_catalog_configuration()

        # assert
        self.assertEqual(["myLocalCatalogCachePath", "https://gitlab.com/album-app/catalogs/default"], r)
        get_cache_path_catalog.assert_called_once_with("catalog_local")

    @patch('album.core.model.configuration.force_remove')
    def test_empty_tmp(self, force_remove_mock):
        force_remove_mock.return_value = None
        # call
        self.conf.empty_tmp()

        force_remove_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
