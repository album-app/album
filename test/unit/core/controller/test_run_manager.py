import unittest
from unittest.mock import MagicMock

from album.core.controller.run_manager import RunManager
from album.core.model.resolve_result import ResolveResult
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestRunManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        """Setup things necessary for all tests of this class"""
        album = self.create_album_test_instance()
        self.create_test_solution_no_env()
        self.run_manager: RunManager = album.run_manager()
        self.collection_manager = album.collection_manager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_run(self):
        # mocks
        build_queue = MagicMock(return_value=None)
        self.album.script_manager().build_queue = build_queue

        run_queue = MagicMock(return_value=None)
        self.album.script_manager().run_queue = run_queue

        # call
        self.run_manager.run(ResolveResult("", None, None, None, self.active_solution), False)

        # assert
        build_queue.assert_called_once()
        run_queue.assert_called_once()


if __name__ == '__main__':
    unittest.main()
