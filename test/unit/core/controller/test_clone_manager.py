import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.model.resolve_result import ResolveResult
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCondaManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_solution_no_env()
        self.clone_manager = self.album_controller.clone_manager()

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_clone(self):
        # todo: implement
        pass

    @patch('album.core.controller.clone_manager.copy_folder', return_value=False)
    def test__clone_solution(self, copy_folder_mock):
        # create mocks
        resolve_result = ResolveResult(
            path=Path("tmp_dir").joinpath("resolving"),
            catalog=None,
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates()
        )

        resolve = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve = resolve

        # call
        p = Path("mypath_to").joinpath("solution")
        t = Path("mytarget").joinpath("def")
        self.clone_manager._clone_solution(p, t)

        # assert
        copy_folder_mock.assert_called_once_with(Path("tmp_dir"), t, copy_root_folder=False)

    @unittest.skip("Needs to be implemented!")
    def test__try_cloning_catalog_template(self):
        # todo: implement
        pass
