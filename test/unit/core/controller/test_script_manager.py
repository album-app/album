import unittest
from queue import Queue
from test.unit.test_unit_core_common import EmptyTestClass, TestUnitCoreCommon
from unittest import mock
from unittest.mock import MagicMock, patch

from album.core.controller.script_manager import ScriptManager
from album.core.model.resolve_result import ResolveResult
from album.core.model.script_queue_entry import ScriptQueueEntry
from album.runner.core.api.model.solution import ISolution


class TestScriptManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        """Setup things necessary for all tests of this class"""
        self.setup_solution_no_env()
        self.script_manager: ScriptManager = self.album_controller.script_manager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_run_queue_empty(self):
        # mocks
        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.script_manager._run_in_environment = _run_in_environment_with_own_logger

        # call
        que = Queue()
        self.script_manager.run_queue(que)

        # assert
        _run_in_environment_with_own_logger.assert_not_called()

    def test_run_queue(self):
        # mocks
        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.script_manager._run_in_environment = _run_in_environment_with_own_logger

        # call
        que = Queue()
        que.put(
            ScriptQueueEntry(
                self.active_solution.coordinates(),
                "path",
                "action",
                ["test"],
                None,
                None,
                None,
            )
        )
        que.put(
            ScriptQueueEntry(
                self.active_solution.coordinates(),
                "path",
                "action",
                ["test2"],
                None,
                None,
                None,
            )
        )
        self.script_manager.run_queue(que)

        # assert
        self.assertEqual(2, _run_in_environment_with_own_logger.call_count)

    def test_create_solution_run_script(self):
        set_environment = MagicMock(return_value=None)
        self.album_controller.environment_manager().set_environment = set_environment

        self.active_solution.script = lambda: "script.py"

        r = self.script_manager._create_solution_script(
            ResolveResult(
                "", None, None, self.active_solution.coordinates(), self.active_solution
            ),
            [],
            ISolution.Action.RUN,
        )

        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual("script.py", r.script)
        set_environment.assert_called_once()

    @unittest.skip("TODO fix implementation")
    def test_create_solution_run_script_standalone_run_and_close(self):
        # TODO this is not actually assigning run or close to the solution and also not checking for it.

        set_environment = MagicMock(return_value=None)
        self.album_controller.environment_manager().set_environment = set_environment

        r = self.script_manager._create_solution_script(
            ResolveResult(
                "", None, None, self.active_solution.coordinates(), self.active_solution
            ),
            [],
            ISolution.Action.RUN,
        )

        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual(["myscript"], r.scripts)
        set_environment.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_create_solution_run_with_parent_script(self):
        # ToDo: implement!
        pass

    @patch("album.runner.album_logging.configure_logging", return_value=None)
    @patch("album.runner.album_logging.push_active_logger", return_value=None)
    @patch("album.runner.album_logging.pop_active_logger", return_value=None)
    def test__run_in_environment(self, pop_mock, push_mock, conf_mock):
        run_script_mock = MagicMock()
        self.album_controller.environment_manager().run_script = run_script_mock

        environment = EmptyTestClass()
        environment.name = lambda: ""
        environment.path = lambda: "path"

        self.active_solution.script = lambda: "script.py"

        self.script_manager._run_in_environment(
            ScriptQueueEntry(
                self.active_solution.coordinates(),
                self.active_solution.script(),
                ISolution.Action.RUN,
                [""],
                environment,
                None,
                None,
            )
        )

        run_script_mock.assert_called_once_with(
            environment,
            "script.py",
            argv=[""],
            environment_variables=mock.ANY,
            pipe_output=True,
        )
        push_mock.assert_not_called()
        pop_mock.assert_not_called()

    def test__get_args(self):
        step = {
            "args": [
                {"name": "test1", "value": lambda args: "test1Value"},
                {"name": "test2", "value": lambda args: "test2Value"},
            ]
        }

        r = self.script_manager._get_args(step, None)

        self.assertEqual(["", "--test1=test1Value", "--test2=test2Value"], r)


if __name__ == "__main__":
    unittest.main()
