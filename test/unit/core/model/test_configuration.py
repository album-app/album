import os
import tempfile
import time
import unittest
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon

from album.core.model.configuration import Configuration, DefaultValues
from album.core.utils.operations.file_operations import create_path_recursively


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
        self._make_stale(leftover_file)

        # assert preparation
        self.assertTrue(leftover_file.exists())

        # call
        conf = Configuration()
        conf.setup(base_cache_path=base_path)

        # assert
        self.assertEqual(base_path, conf.base_cache_path())

        # leftovers should be removed by now
        self.assertFalse(leftover_file.exists())

        # the instance has its own temporary folder inside the tmp folder
        self.assertEqual([conf._tmp_path], list(c_path.iterdir()))
        self.assertEqual(conf._tmp_path, conf.tmp_path())

        # check if all recursive paths are created
        self.assertTrue(base_path.exists())
        self.assertTrue(conf.base_cache_path().exists())
        self.assertTrue(conf.cache_path_download().exists())

        # _catalog_collection_path is the folder, the get_catalog_collection_path()
        # points to the collection database in that folder
        self.assertTrue(conf._catalog_collection_path.exists())
        self.assertTrue(conf.installation_path().exists())
        self.assertTrue(conf.lnk_path().exists())
        self.assertTrue(conf.environments_path().exists())
        self.assertTrue(conf.shared_resources_path().exists())

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

    def test_setup_keeps_tmp_of_other_instance(self):
        # prepare
        base_path = Path(self.tmp_dir.name).joinpath("base_path")
        conf = Configuration()
        conf.setup(base_cache_path=base_path)
        file_in_use = conf.tmp_path().joinpath("file_in_use")
        file_in_use.touch()

        # call
        other_conf = Configuration()
        other_conf.setup(base_cache_path=base_path)

        # assert
        self.assertNotEqual(conf.tmp_path(), other_conf.tmp_path())
        self.assertEqual(conf.tmp_path().parent, other_conf.tmp_path().parent)
        self.assertTrue(file_in_use.exists())

    def test_close(self):
        # prepare
        base_path = Path(self.tmp_dir.name).joinpath("base_path")
        conf = Configuration()
        conf.setup(base_cache_path=base_path)
        other_conf = Configuration()
        other_conf.setup(base_cache_path=base_path)
        tmp_path = conf.tmp_path()
        other_tmp_path = other_conf.tmp_path()
        tmp_path.joinpath("a_file").touch()

        # call
        conf.close()

        # assert
        self.assertFalse(tmp_path.exists())
        self.assertTrue(other_tmp_path.exists())

        # closing twice is fine, the folder is created again when it is used
        conf.close()
        self.assertTrue(conf.tmp_path().exists())

    def test_close_album_controller(self):
        # prepare
        tmp_path = self.album_controller.configuration().tmp_path()

        # call
        self.album_controller.close()

        # assert
        self.assertFalse(tmp_path.exists())

    def test_remove_stale_tmp(self):
        # prepare
        base_path = Path(self.tmp_dir.name).joinpath("base_path")
        tmp_root_path = base_path.joinpath(DefaultValues.cache_path_tmp_prefix.value)
        stale_folder = tmp_root_path.joinpath("stale_folder")
        fresh_folder = tmp_root_path.joinpath("fresh_folder")
        create_path_recursively(stale_folder.joinpath("content"))
        create_path_recursively(fresh_folder.joinpath("content"))
        self._make_stale(stale_folder)

        # call
        conf = Configuration()
        conf.setup(base_cache_path=base_path)

        # assert
        self.assertFalse(stale_folder.exists())
        self.assertTrue(fresh_folder.joinpath("content").exists())
        self.assertTrue(conf._tmp_path.exists())

    @staticmethod
    def _make_stale(path):
        stale_time = time.time() - DefaultValues.stale_tmp_age_in_seconds.value - 60
        os.utime(path, (stale_time, stale_time))


if __name__ == "__main__":
    unittest.main()
