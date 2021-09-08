import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from album.core.model.configuration import Configuration, DefaultValues
from album.core.utils.operations.file_operations import create_path_recursively
from test.unit.test_unit_common import TestUnitCommon


class TestConfiguration(TestUnitCommon):

    def setUp(self) -> None:
        super().setUp()
        self.conf = Configuration()
        self.conf.setup(base_cache_path=Path(self.tmp_dir.name).joinpath("album"),
                        configuration_file_path=self.tmp_dir.name)

    def tearDown(self) -> None:
        super().tearDown()

    def test_setup(self):
        # prepare
        base_path = Path(self.tmp_dir.name).joinpath("base_path")
        c_path = base_path.joinpath(DefaultValues.cache_path_tmp_prefix.value)
        create_path_recursively(c_path)
        leftover_file = c_path.joinpath("a_leftover_file")
        leftover_file.touch()

        # assert preparation
        self.assertTrue(leftover_file.exists())

        # call
        self.conf.setup(base_cache_path=base_path,
                        configuration_file_path=Path(self.tmp_dir.name).joinpath("conf_file_folder"))

        # assert
        self.assertFalse(leftover_file.exists())
        self.assertEqual(DefaultValues.conda_path.value, self.conf.conda_executable)
        self.assertEqual(base_path, self.conf.base_cache_path)

    def test_base_cache_path(self):
        new_tmp_dir = tempfile.TemporaryDirectory(dir=self.tmp_dir.name)

        # set
        self.conf.base_cache_path = new_tmp_dir.name

        # assert
        self.assertEqual(
            Path(new_tmp_dir.name),
            self.conf.base_cache_path
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
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value),
            self.conf.catalog_collection_path
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

    @unittest.skip("Needs to be implemented!")
    def test_get_catalog_collection_path(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_catalog_collection_meta_dict(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_catalog_collection_meta_path(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_initial_catalogs(self):
        # todo: implement
        pass

    @patch('album.core.model.configuration.force_remove')
    def test_empty_tmp(self, force_remove_mock):
        force_remove_mock.return_value = None
        # call
        self.conf.empty_tmp()

        force_remove_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
