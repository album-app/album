import unittest
from copy import deepcopy
from queue import Queue
from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.script_manager import ScriptManager
from album.core.model.resolve_result import ResolveResult
from album.core.model.script_queue_entry import ScriptQueueEntry
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestUnitCoreCommon, EmptyTestClass


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

    def test_create_solution_run_script_standalone(self):
        set_environment = MagicMock(return_value=None)
        self.album_controller.environment_manager().set_environment = set_environment

        self.active_solution.script = lambda: "script.py"

        r = self.script_manager._create_solution_run_script_standalone(
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

        r = self.script_manager._create_solution_run_script_standalone(
            ResolveResult(
                "", None, None, self.active_solution.coordinates(), self.active_solution
            ),
            [],
            ISolution.Action.RUN,
        )

        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual(["myscript"], r.scripts)
        set_environment.assert_called_once()

    def test_create_solution_run_with_parent_script_standalone(self):
        # prepare
        self.setup_collection()
        self.active_solution._setup.dependencies = {
            "parent": {"name": "aParent", "group": "grp", "version": "v1"}
        }
        self.active_solution.script = lambda: "script.py"

        # mock
        catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.script_manager._resolve_args = resolve_args

        set_environment = MagicMock(return_value=None)
        self.album_controller.environment_manager().set_environment = set_environment

        # call
        r = self.script_manager._create_solution_run_with_parent_script_standalone(
            ResolveResult(
                path="aPath",
                catalog=catalog,
                loaded_solution=self.active_solution,
                collection_entry=None,
                coordinates=self.active_solution.coordinates(),
            ),
            [],
            ISolution.Action.RUN,
        )

        # assertipt.assert_called_once_with(self.active_solution, "active_solution_args")
        set_environment.assert_called_once()

        # result
        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual("script.py", r.script)

    @unittest.skip("Needs to be implemented!")
    def test_create_solution_run_with_parent_script(self):
        # ToDo: implement!
        pass

    def test_resolve_args(self):
        # the arguments of the steps solution for each step
        steps = [
            {
                "name": "Step1",
                "args": [{"name": "s1_arg1", "value": lambda args: "s1_arg1_value"}],
            },
            {
                "name": "Step2",
                "args": [{"name": "s2_arg1", "value": lambda args: "s2_arg1_value"}],
            },
        ]

        # solution object and arguments of the first solution mentioned in the steps above
        step1_solution = self.active_solution
        step1_solution._setup.dependencies = {
            "parent": {
                "name": "app1",
                "args": [
                    {"name": "parent_arg1", "value": "parent_arg1_value"},
                    {"name": "parent_arg2", "value": "parent_arg2_value"},
                ],
            }
        }
        # Todo: the arguments of the step description contradict with the one the step1 one actually needs!!!
        step1_solution._setup.args = [
            {"name": "arg1_step1", "value": "arg1val_step1"},
            {"name": "arg2_step1", "value": "arg2val_step1"},
        ]

        # solution object and arguments of the second solution mentioned in the steps above
        step2_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        step2_solution._setup.dependencies = {
            "parent": {
                "name": "app1",
                "args": [
                    {
                        "name": "parent_arg1",
                        "value": "parent_arg1_contradicting_value_with_other_definition!",
                    },
                    {"name": "parent_arg2", "value": "parent_arg2_value"},
                ],
            }
        }

        step2_solution._setup.args = [
            {"name": "arg1_step2", "value": "arg1val_step2"},
            {"name": "arg2_step2", "value": "arg2val_step2"},
        ]

        # the parent solution of both and its argument
        parent_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        parent_solution._setup.args = [
            {
                "name": "parent_arg1",
                "default": "",
                "description": "",
            },
            {
                "name": "parent_arg2",
                "default": "",
                "description": "",
            },
        ]

        parsed_parent_args, parsed_steps_args_list = self.script_manager._resolve_args(
            parent_solution,
            [step1_solution, step2_solution],
            steps,
            [
                None
            ],  # mocks the namespace object from the argument parsing of the parent
            args=None,
        )

        self.assertEqual(
            ["", "--parent_arg1=parent_arg1_value", "--parent_arg2=parent_arg2_value"],
            parsed_parent_args,
        )
        self.assertEqual(
            [["", "--s1_arg1=s1_arg1_value"], ["", "--s2_arg1=s2_arg1_value"]],
            parsed_steps_args_list,
        )

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
            environment, "script.py", argv=[""], environment_variables=mock.ANY
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
