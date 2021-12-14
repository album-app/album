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
        conf = Configuration()
        conf.setup(base_cache_path=base_path)

        # assert
        self.assertFalse(leftover_file.exists())
        self.assertEqual(DefaultValues.conda_path.value, conf.conda_executable())
        self.assertEqual(base_path, conf.base_cache_path())

    def test_base_cache_path(self):
        new_tmp_dir = tempfile.TemporaryDirectory(dir=self.tmp_dir.name)

        # set
        conf = Configuration()
        conf.setup(base_cache_path=new_tmp_dir.name)

        # assert
        self.assertEqual(
            Path(new_tmp_dir.name),
            conf.base_cache_path()
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_solution_prefix.value),
            conf.cache_path_tmp_internal()
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_app_prefix.value),
            conf.cache_path_app()
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_download_prefix.value),
            conf.cache_path_download()
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.cache_path_tmp_prefix.value),
            conf.cache_path_tmp_user()
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, DefaultValues.catalog_collection_db_name.value),
            conf.get_catalog_collection_path()
        )

    @unittest.skipUnless(sys.platform.startswith("win"), "requires Windoofs")
    def test__build_conda_executable_windows(self):
        conf = Configuration()
        r = conf._build_conda_executable("myPathToConda")

        expected = Path("myPathToConda").joinpath("Scripts", "conda.exe")
        self.assertEqual(r, str(expected))

    @unittest.skipUnless(sys.platform == 'linux' or sys.platform == 'darwin', "requires a proper OS")
    def test__build_conda_executable_linux(self):
        conf = Configuration()
        r = conf._build_conda_executable("myPathToConda")

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
        conf = Configuration()
        conf._cache_path_tmp_user = Path(self.tmp_dir.name)
        conf._empty_tmp()

        force_remove_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
