import os
import unittest
from pathlib import Path
from unittest.mock import patch

import pkg_resources

from album.core.utils.export.conda_lock import create_conda_lock_file
from album.core.utils.operations.file_operations import copy
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCondaLock(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_create_conda_lockfile(self):
        # prepare
        yml_path = Path(self.tmp_dir.name).joinpath("test.yml")
        env_file = Path(os.path.dirname(os.path.realpath(__file__))).joinpath("..", "..", "..", "..","resources",
                                                                              "test_env_file.yml")
        copy(env_file, yml_path)

        # call
        lock_file = create_conda_lock_file(yml_path, self.album_controller.configuration().conda_lock_executable())

        # assert
        self.assertTrue(lock_file.is_file())
        self.assertEqual("solution.conda-lock.yml", lock_file.name)
        self.assertEqual(yml_path.parent, lock_file.parent)
        self.assertNotEquals(lock_file.stat().st_size, 0)
