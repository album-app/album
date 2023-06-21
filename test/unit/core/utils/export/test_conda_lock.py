from pathlib import Path

from album.core.utils.export.conda_lock import create_conda_lock_file
from album.core.utils.operations.file_operations import write_dict_to_yml
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCondaLock(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_create_conda_lockfile(self):
        # prepare
        yml_dict = {
            "name": "t",
            "channels": ["conda-forge"],
            "dependencies": ["python"]
        }
        yml_path = Path(self.tmp_dir.name).joinpath("test.yml")
        write_dict_to_yml(
            yml_path, yml_dict
        )

        # call
        lock_file = create_conda_lock_file(yml_path, self.album_controller.configuration().conda_lock_executable())

        # assert
        self.assertTrue(lock_file.is_file())
        self.assertEqual("solution.conda-lock.yml", lock_file.name)
        self.assertEqual(yml_path.parent, lock_file.parent)
        self.assertNotEqual(lock_file.stat().st_size, 0)
