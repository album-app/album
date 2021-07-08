import unittest
from copy import deepcopy
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, call
from unittest.mock import patch

from album.core.controller.resolve_manager import ResolveManager
from album.core.controller.run_manager import RunManager
from album_runner.logging import LogLevel
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestRunManager(TestUnitCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.create_test_config()
        self.create_test_solution_no_env()

        # always re-initialize RunManager
        with patch.object(RunManager, '__init__', return_value=None) as init_mock:
            RunManager.instance = None
            self.run_manager = RunManager()
            self.run_manager.resolve_manager = ResolveManager(self.test_catalog_collection)
            self.run_manager.init_script = ""
            init_mock.assert_called_once()

    def tearDown(self) -> None:
        super().tearDown()

    def test_run(self):
        # mocks
        catalog = EmptyTestClass()
        catalog.id = "niceId"

        resolve_and_load = MagicMock(return_value=[{"path": "aPath", "catalog": catalog}, self.active_solution])
        self.run_manager.resolve_manager.resolve_and_load = resolve_and_load

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        _run = MagicMock(return_value=None)
        self.run_manager._run = _run

        _resolve_installed = MagicMock(return_value={"path": Path(self.closed_tmp_file.name), "catalog": None})
        self.run_manager.resolve_manager._resolve_installed = _resolve_installed

        self.run_manager.resolve_manager.catalog_collection = self.test_catalog_collection

        # test
        self.run_manager.run(self.closed_tmp_file.name)

        # assert
        _run.assert_called_once_with(self.active_solution, False)
        resolve_and_load.assert_called_once_with(self.closed_tmp_file.name, mode="c")

    def test__run(self):
        # mocks
        build_queue = MagicMock(return_value=None)
        self.run_manager.build_queue = build_queue

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        self.run_manager._run(self.active_solution, False)

        # assert
        build_queue.assert_called_once()
        run_queue.assert_called_once()

    def test_build_queue_steps_list(self):
        self.active_solution.steps = [["step1A", "step1B"], "step2"]

        # mocks
        build_steps_queue = MagicMock(return_value=None)
        self.run_manager.build_steps_queue = build_steps_queue

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        create_solution_run_with_parent_script_standalone = MagicMock(return_value=None)
        self.run_manager.create_solution_run_with_parent_script_standalone = create_solution_run_with_parent_script_standalone

        create_solution_run_script_standalone = MagicMock(return_value=None)
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        # call
        que = Queue()
        self.run_manager.build_queue(self.active_solution, que, False)

        # assert
        self.assertEqual(2, build_steps_queue.call_count)

        run_queue.assert_not_called()
        create_solution_run_with_parent_script_standalone.assert_not_called()
        create_solution_run_script_standalone.assert_not_called()

    def test_build_queue_steps_single(self):
        # mocks
        build_steps_queue = MagicMock(return_value=None)
        self.run_manager.build_steps_queue = build_steps_queue

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        create_solution_run_with_parent_script_standalone = MagicMock(return_value=None)
        self.run_manager.create_solution_run_with_parent_script_standalone = create_solution_run_with_parent_script_standalone

        create_solution_run_script_standalone = MagicMock(return_value=None)
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        # call
        que = Queue()
        self.run_manager.build_queue(self.active_solution, que, False)

        # assert
        build_steps_queue.assert_not_called()
        run_queue.assert_not_called()
        create_solution_run_with_parent_script_standalone.assert_not_called()
        create_solution_run_script_standalone.assert_called_once()

    def test_run_queue_empty(self):
        # mocks
        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.run_manager._run_in_environment_with_own_logger = _run_in_environment_with_own_logger

        # call
        que = Queue()
        self.run_manager.run_queue(que)

        # assert
        _run_in_environment_with_own_logger.assert_not_called()
        self.assertIn("Currently nothing more to run!", self.captured_output.getvalue())

    def test_run_queue(self):
        # mocks
        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.run_manager._run_in_environment_with_own_logger = _run_in_environment_with_own_logger

        # call
        que = Queue()
        que.put([self.active_solution, ["test"]])
        que.put([self.active_solution, ["test2"]])
        self.run_manager.run_queue(que)

        # assert
        self.assertEqual(2, _run_in_environment_with_own_logger.call_count)
        self.assertIn("Currently nothing more to run!", self.captured_output.getvalue())

    def test_build_steps_queue_no_parent(self):
        # mock
        catalog = EmptyTestClass()
        catalog.id = "niceId"
        resolve_dependency_and_load = MagicMock(return_value=[{"path": "aPath", "catalog": catalog}, self.active_solution])
        self.run_manager.resolve_manager.resolve_dependency_and_load = resolve_dependency_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager.create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        self.run_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        que = Queue()
        steps = [{"name": "Step1", },
                 {"name": "Step2", }]

        self.run_manager.build_steps_queue(que, steps, False)

        # assert
        self.assertEqual(2, resolve_dependency_and_load.call_count)  # 2 steps
        self.assertEqual(2, _get_args.call_count)  # 2 times arguments resolved
        self.assertEqual(2, create_solution_run_script_standalone.call_count)  # 2 times standalone script created
        create_solution_run_collection_script.assert_not_called()
        run_queue.assert_not_called()

        # result
        res_que = Queue()
        res_que.put("runScriptStandalone")
        res_que.put("runScriptStandalone")

        self.assertEqual(res_que.qsize(), que.qsize())
        self.assertEqual(res_que.get(), que.get(block=False))
        self.assertEqual(res_que.get(), que.get(block=False))

    def test_build_steps_queue_parent(self):
        self.active_solution.parent = "aParent"

        # mocks
        catalog = EmptyTestClass()
        catalog.id = "niceId"

        resolve_dependency_and_load = MagicMock(return_value=[{"path": "aPath", "catalog": catalog}, self.active_solution])
        self.run_manager.resolve_manager.resolve_dependency_and_load = resolve_dependency_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager.create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        self.run_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        que = Queue()
        steps = [{"name": "Step1", },
                 {"name": "Step2", }]

        self.run_manager.build_steps_queue(que, steps, False)

        # assert
        self.assertEqual(4,
                         resolve_dependency_and_load.call_count)  # 2 times step, 2 times parent
        self.assertEqual(0, _get_args.call_count)  # 0 times arguments resolved
        self.assertEqual(0, create_solution_run_script_standalone.call_count)  # 0 times standalone script created

        create_solution_run_collection_script.assert_called_once_with({
            "parent_script_path": "aPath",
            "parent_script_catalog": catalog,
            "steps_solution": [self.active_solution, self.active_solution],
            "steps": steps
        })
        run_queue.assert_not_called()

        # result
        res_que = Queue()
        res_que.put("runScriptCollection")

        self.assertEqual(res_que.qsize(), que.qsize())
        self.assertEqual(res_que.get(), que.get(block=False))

    def test_build_steps_queue_run_immediately(self):
        # mock
        catalog = EmptyTestClass()
        catalog.id = "niceId"


        resolve_dependency_and_load = MagicMock(return_value=[{"path": "aPath", "catalog": catalog}, self.active_solution])
        self.run_manager.resolve_manager.resolve_dependency_and_load = resolve_dependency_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager.create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        self.run_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        que = Queue()
        steps = [{"name": "Step1", }]

        self.run_manager.build_steps_queue(que, steps, True)

        # assert
        self.assertEqual(1, resolve_dependency_and_load.call_count)  # 1 tep resolved
        self.assertEqual(1, _get_args.call_count)  # 1 times arguments resolved
        self.assertEqual(1, create_solution_run_script_standalone.call_count)  # 1 times standalone script created
        create_solution_run_collection_script.assert_not_called()
        self.assertEqual(2, run_queue.call_count)  # once to immediately run, once to clear que

    @patch('album.core.controller.run_manager.create_script', return_value=None)
    def test_create_solution_run_script_standalone_no_run(self, create_script_mock):
        with self.assertRaises(ValueError):
            self.run_manager.create_solution_run_script_standalone(self.active_solution, [])

        create_script_mock.assert_not_called()

    @patch('album.core.controller.run_manager.create_script', return_value="aScript")
    def test_create_solution_run_script_standalone(self, create_script_mock):
        self.active_solution.run = print

        r = self.run_manager.create_solution_run_script_standalone(self.active_solution, [])

        self.assertEqual([self.active_solution, ["aScript"]], r)
        create_script_mock.assert_called_once_with(self.active_solution, "\nget_active_solution().run()\n", [])

    @patch('album.core.controller.run_manager.create_script', return_value="aScript")
    def test_create_solution_run_script_standalone_run_and_close(self, create_script_mock):
        self.active_solution.run = print
        self.active_solution.close = print

        r = self.run_manager.create_solution_run_script_standalone(self.active_solution, [])

        self.assertEqual([self.active_solution, ["aScript"]], r)
        create_script_mock.assert_called_once_with(
            self.active_solution, "\nget_active_solution().run()\n\nget_active_solution().close()\n", []
        )

    def test_create_solution_run_with_parent_script_standalone(self):
        self.active_solution.parent = {"name": "aParent"}

        # mock
        catalog = EmptyTestClass()
        catalog.id = "niceId"
        resolve_dependency_and_load = MagicMock(return_value=[{"path": "aPath", "catalog": catalog}, self.active_solution])
        self.run_manager.resolve_manager.resolve_dependency_and_load = resolve_dependency_and_load

        create_solution_run_with_parent_scrip = MagicMock(return_value="aScript")
        self.run_manager.create_solution_run_with_parent_script = create_solution_run_with_parent_scrip

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.run_manager.resolve_args = resolve_args

        # call
        self.run_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        r = self.run_manager.create_solution_run_with_parent_script_standalone(self.active_solution, [])

        # assert
        resolve_args.assert_called_once_with(self.active_solution, [self.active_solution], [None], [])
        create_solution_run_with_parent_scrip.assert_called_once_with(
            self.active_solution, "parent_args", [self.active_solution], "active_solution_args"
        )
        resolve_dependency_and_load.assert_called_once()

        # result
        self.assertEqual([self.active_solution, "aScript"], r)

    @patch('album.core.controller.run_manager.load')
    def test_create_solution_run_collection_script(self, load_mock):
        # mock
        load_mock.return_value = self.active_solution
        catalog = EmptyTestClass()
        catalog.id = "niceId"

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.run_manager.resolve_args = resolve_args

        create_solution_run_with_parent_scrip = MagicMock(return_value="aScript")
        self.run_manager.create_solution_run_with_parent_script = create_solution_run_with_parent_scrip

        # prepare
        self.active_solution.parent = {"name": "aParent"}
        p = {
            "parent_script_path": "aPathToaParent",
            "parent_script_catalog": catalog,
            "steps_solution": [self.active_solution, self.active_solution],
            "steps": ["step1", "step2"]
        }

        # call
        r = self.run_manager.create_solution_run_collection_script(p)

        # assert
        resolve_args.assert_called_once_with(self.active_solution, [self.active_solution, self.active_solution], ["step1", "step2"])
        create_solution_run_with_parent_scrip.assert_called_once_with(
            self.active_solution, "parent_args", [self.active_solution, self.active_solution], "active_solution_args"
        )

        # result
        self.assertEqual([self.active_solution, "aScript"], r)

    @patch('album.core.controller.run_manager.create_script')
    def test_create_solution_run_with_parent_scrip(self, create_script_mock):
        create_script_mock.side_effect = ["script_paretn", "script_child_1", "script_child_2"]

        r = self.run_manager.create_solution_run_with_parent_script(
            self.active_solution, [], [self.active_solution, self.active_solution], [[], []]
        )

        # assert
        calls = [
            call(self.active_solution, "\nget_active_solution().run()\n", []),
            call(self.active_solution,
                 "\nmodule_logger().info(\"Started tsn\")\n\nget_active_solution().run()\n\nmodule_logger().info(\"Finished tsn\")\n\npop_active_solution()\n",
                 []),
            call(self.active_solution,
                 "\nmodule_logger().info(\"Started tsn\")\n\nget_active_solution().run()\n\nmodule_logger().info(\"Finished tsn\")\n\npop_active_solution()\n",
                 []),
        ]
        self.assertEqual(3, create_script_mock.call_count)
        create_script_mock.assert_has_calls(calls)

        # result
        self.assertEqual(["script_paretn", "script_child_1", "script_child_2", "\npop_active_solution()\n"], r)

    def test_resolve_args(self):
        # the arguments of the steps hip solution for each step
        steps = [
            {
                "name": "Step1",
                "args": [{"name": "s1_arg1", "value": lambda: "s1_arg1_value"}]
            },
            {
                "name": "Step2",
                "args": [{"name": "s2_arg1", "value": lambda: "s2_arg1_value"}]
            }
        ]

        # album object and arguments of the first hip solution mentioned in the steps above
        step1_solution = self.active_solution
        step1_solution.parent = {
            'name': 'app1',
            'args': [
                {
                    "name": "parent_arg1",
                    "value": "parent_arg1_value"
                },
                {
                    "name": "parent_arg2",
                    "value": "parent_arg2_value"
                }
            ]
        }
        # Todo: the arguments of the step description contradict with the one the step1 one actually needs!!!
        step1_solution.args = [
            {
                "name": "arg1_step1",
                "value": "arg1val_step1"
            }, {
                "name": "arg2_step1",
                "value": "arg2val_step1"
            }
        ]

        #  album object and arguments of the second hip solution mentioned in the steps above
        step2_solution = deepcopy(self.active_solution)
        step2_solution.parent = {
            'name': 'app1',
            'args': [
                {
                    "name": "parent_arg1",
                    "value": "parent_arg1_contradicting_value_with_other_definition!"
                },
                {
                    "name": "parent_arg2",
                    "value": "parent_arg2_value"
                }
            ]
        }
        step2_solution.args = [
            {
                "name": "arg1_step2",
                "value": "arg1val_step2"
            }, {
                "name": "arg2_step2",
                "value": "arg2val_step2"
            }
        ]

        # the parent hip of both and its argument
        parent_solution = deepcopy(self.active_solution)
        parent_solution.args = [{
            "name": "parent_arg1",
            "default": "",
            "description": "",
        }, {
            "name": "parent_arg2",
            "default": "",
            "description": "",
        }]

        parsed_parent_args, parsed_steps_args_list = self.run_manager.resolve_args(
            parent_solution,
            [step1_solution, step2_solution],
            steps
        )

        self.assertEqual(['', '--parent_arg1=parent_arg1_value', '--parent_arg2=parent_arg2_value'], parsed_parent_args)
        self.assertEqual([['', '--s1_arg1=s1_arg1_value'], ['', '--s2_arg1=s2_arg1_value']], parsed_steps_args_list)

    @patch('album_runner.logging.configure_logging', return_value=None)
    @patch('album_runner.logging.pop_active_logger', return_value=None)
    def test__run_in_environment_with_own_logger(self, pop_mock, conf_mock):
        class TestEnvironment:
            @staticmethod
            def run_scripts(script):
                return script

        self.active_solution.environment = TestEnvironment()

        self.run_manager._run_in_environment_with_own_logger(self.active_solution, "")

        conf_mock.assert_called_once_with(LogLevel(0), self.active_solution["name"])

        pop_mock.assert_called_once()

    def test__get_args(self):
        step = {
            "args": [
                {
                    "name": "test1",
                    "value": lambda: "test1Value"
                },
                {
                    "name": "test2",
                    "value": lambda: "test2Value"
                }
            ]
        }

        r = self.run_manager._get_args(step)

        self.assertEqual(["", "--test1=test1Value", "--test2=test2Value"], r)


if __name__ == '__main__':
    unittest.main()
