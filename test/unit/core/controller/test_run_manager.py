import unittest
from unittest import mock
from unittest.mock import MagicMock, patch, create_autospec

from album.core.controller.run_manager import RunManager
from album.core.model.resolve_result import ResolveResult
from test.unit.test_unit_core_common import TestUnitCoreCommon, EmptyTestClass


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

    @patch('pkg_resources.iter_entry_points')
    def test_load_plugins(self, iter_entry_points):
        entry_point = EmptyTestClass()
        entry_point.name = "plugin-name"
        entry_point_load = MagicMock()
        entry_point_load_return = MagicMock()
        entry_point_load.return_value = entry_point_load_return
        entry_point.load = entry_point_load
        iter_entry_points.return_value = [entry_point]
        resolve_result = create_autospec(ResolveResult)
        self.active_solution._setup["dependencies"] = {}
        self.active_solution._setup["dependencies"]["plugins"] = [
            {
                "id": "plugin-name"
            }
        ]
        resolve_result.loaded_solution = lambda: self.active_solution
        self.album_controller.run_manager().load_plugins(resolve_result)
        entry_point_load_return.assert_called_with(mock.ANY, resolve_result.coordinates.return_value, {})

    @patch('pkg_resources.iter_entry_points')
    def test_load_plugins_not_found(self, iter_entry_points):
        iter_entry_points.return_value = []
        resolve_result = create_autospec(ResolveResult)
        self.active_solution._setup["dependencies"] = {}
        self.active_solution._setup["dependencies"]["plugins"] = [
            {
                "id": "plugin-name"
            }
        ]
        resolve_result.loaded_solution = lambda: self.active_solution
        with self.assertRaises(LookupError):
            self.album_controller.run_manager().load_plugins(resolve_result)


    @patch('pkg_resources.iter_entry_points')
    def test_load_plugins_with_args(self, iter_entry_points):
        entry_point = EmptyTestClass()
        entry_point.name = "plugin-name"
        entry_point_load = MagicMock()
        entry_point_load_return = MagicMock()
        entry_point_load.return_value = entry_point_load_return
        entry_point.load = entry_point_load
        iter_entry_points.return_value = [entry_point]
        resolve_result = create_autospec(ResolveResult)
        self.active_solution._setup["dependencies"] = {}
        self.active_solution._setup["dependencies"]["plugins"] = [
            {
                "id": "plugin-name",
                "args": {
                    "my-arg": "arg-value"
                }
            }
        ]
        resolve_result.loaded_solution = lambda: self.active_solution
        self.album_controller.run_manager().load_plugins(resolve_result)
        entry_point_load_return.assert_called_with(mock.ANY, resolve_result.coordinates.return_value, {"my-arg": "arg-value"})


if __name__ == '__main__':
    unittest.main()
