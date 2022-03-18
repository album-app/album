import unittest
from unittest.mock import MagicMock

from album.core.controller.run_manager import RunManager
from album.core.model.resolve_result import ResolveResult
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestRunManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        """Setup things necessary for all tests of this class"""
        self.setup_solution_no_env()
        self.run_manager: RunManager = self.album_controller.run_manager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_run(self):
        # mocks
        build_queue = MagicMock(return_value=None)
        self.album_controller.script_manager().build_queue = build_queue

        run_queue = MagicMock(return_value=None)
        self.album_controller.script_manager().run_queue = run_queue

        resolve_result = ResolveResult("", None, None, None, self.active_solution)

        resolve_installed_and_load = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve_installed_and_load = resolve_installed_and_load

        # call
        self.run_manager.run("", False)

        # assert
        build_queue.assert_called_once()
        run_queue.assert_called_once()


if __name__ == '__main__':
    unittest.main()
