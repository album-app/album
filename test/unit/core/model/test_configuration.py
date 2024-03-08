import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from album.core.model.configuration import Configuration, DefaultValues
from album.core.utils.operations.file_operations import create_path_recursively
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestConfiguration(TestUnitCoreCommon):
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
        self.assertEqual(base_path, conf.base_cache_path())

    def test_base_cache_path(self):
        new_tmp_dir = tempfile.TemporaryDirectory(dir=self.tmp_dir.name)

        # set
        conf = Configuration()
        conf.setup(base_cache_path=new_tmp_dir.name)

        # assert
        self.assertEqual(Path(new_tmp_dir.name), conf.base_cache_path())
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(
                DefaultValues.installation_folder_prefix.value
            ),
            conf.installation_path(),
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(
                DefaultValues.cache_path_download_prefix.value
            ),
            conf.cache_path_download(),
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(
                DefaultValues.catalog_folder_prefix.value,
                DefaultValues.catalog_collection_db_name.value,
            ),
            conf.get_catalog_collection_path(),
        )

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

    @patch("album.core.model.configuration.force_remove")
    def test_empty_tmp(self, force_remove_mock):
        force_remove_mock.return_value = None
        # call
        conf = Configuration()
        conf._cache_path_tmp_user = Path(self.tmp_dir.name)
        conf._empty_tmp()

        force_remove_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
