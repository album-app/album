import unittest
from copy import deepcopy
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, call
from unittest.mock import patch

from hips.core.controller.run_manager import RunManager
from hips_runner.logging import LogLevel
from test.unit.test_common import TestHipsCommon


class TestRunManager(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.create_test_config()
        self.create_test_hips_no_env()

        with patch.object(RunManager, '__init__', return_value=None) as init_mock:
            RunManager.instance = None
            self.hips_runner = RunManager()
            self.hips_runner.init_script = ""
            init_mock.assert_called_once()

    def tearDown(self) -> None:
        super().tearDown()
        RunManager.instance = None

    @patch('hips.core.controller.run_manager.load')
    def test_run(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        resolve_from_str = MagicMock(return_value={"path": Path(self.closed_tmp_file.name), "catalog": None})
        self.test_catalog_collection.resolve_from_str = resolve_from_str

        _run = MagicMock(return_value=None)
        self.hips_runner._run = _run

        self.hips_runner.catalog_collection = self.test_catalog_collection

        # test
        self.hips_runner.run(self.closed_tmp_file.name)

        # assert
        _run.assert_called_once_with(self.active_hips, False)
        load_mock.assert_called_once_with(Path(self.closed_tmp_file.name))

    def test__run(self):
        # mocks
        build_queue = MagicMock(return_value=None)
        self.hips_runner.build_queue = build_queue

        run_queue = MagicMock(return_value=None)
        self.hips_runner.run_queue = run_queue

        # call
        self.hips_runner._run(self.active_hips, False)

        # assert
        build_queue.assert_called_once()
        run_queue.assert_called_once()

    def test_build_queue_steps_list(self):
        self.active_hips.steps = [["step1A", "step1B"], "step2"]

        # mocks
        build_steps_queue = MagicMock(return_value=None)
        self.hips_runner.build_steps_queue = build_steps_queue

        run_queue = MagicMock(return_value=None)
        self.hips_runner.run_queue = run_queue

        create_hips_run_with_parent_script_standalone = MagicMock(return_value=None)
        self.hips_runner.create_hips_run_with_parent_script_standalone = create_hips_run_with_parent_script_standalone

        create_hips_run_script_standalone = MagicMock(return_value=None)
        self.hips_runner.create_hips_run_script_standalone = create_hips_run_script_standalone

        self.hips_runner.catalog_collection = self.test_catalog_collection

        # call
        que = Queue()
        self.hips_runner.build_queue(self.active_hips, que, False)

        # assert
        self.assertEqual(2, build_steps_queue.call_count)

        run_queue.assert_not_called()
        create_hips_run_with_parent_script_standalone.assert_not_called()
        create_hips_run_script_standalone.assert_not_called()

    def test_build_queue_steps_single(self):
        # mocks
        build_steps_queue = MagicMock(return_value=None)
        self.hips_runner.build_steps_queue = build_steps_queue

        run_queue = MagicMock(return_value=None)
        self.hips_runner.run_queue = run_queue

        create_hips_run_with_parent_script_standalone = MagicMock(return_value=None)
        self.hips_runner.create_hips_run_with_parent_script_standalone = create_hips_run_with_parent_script_standalone

        create_hips_run_script_standalone = MagicMock(return_value=None)
        self.hips_runner.create_hips_run_script_standalone = create_hips_run_script_standalone

        self.hips_runner.catalog_collection = self.test_catalog_collection

        # call
        que = Queue()
        self.hips_runner.build_queue(self.active_hips, que, False)

        # assert
        build_steps_queue.assert_not_called()
        run_queue.assert_not_called()
        create_hips_run_with_parent_script_standalone.assert_not_called()
        create_hips_run_script_standalone.assert_called_once()

    def test_run_queue_empty(self):
        # mocks
        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.hips_runner._run_in_environment_with_own_logger = _run_in_environment_with_own_logger

        # call
        que = Queue()
        self.hips_runner.run_queue(que)

        # assert
        _run_in_environment_with_own_logger.assert_not_called()
        self.assertIn("Currently nothing more to run!", self.captured_output.getvalue())

    def test_run_queue(self):
        # mocks
        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.hips_runner._run_in_environment_with_own_logger = _run_in_environment_with_own_logger

        # call
        que = Queue()
        que.put([self.active_hips, ["test"]])
        que.put([self.active_hips, ["test2"]])
        self.hips_runner.run_queue(que)

        # assert
        self.assertEqual(2, _run_in_environment_with_own_logger.call_count)
        self.assertIn("Currently nothing more to run!", self.captured_output.getvalue())

    @patch('hips.core.controller.run_manager.load')
    def test_build_steps_queue_no_parent(self, load_mock):
        # mock
        load_mock.return_value = self.active_hips

        resolve_hips_dependency = MagicMock(return_value={"path": "aPath"})
        self.test_catalog_collection.resolve_hips_dependency = resolve_hips_dependency

        create_hips_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.hips_runner.create_hips_run_collection_script = create_hips_run_collection_script

        create_hips_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.hips_runner.create_hips_run_script_standalone = create_hips_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.hips_runner._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.hips_runner.run_queue = run_queue

        # call
        self.hips_runner.catalog_collection = self.test_catalog_collection
        que = Queue()
        steps = [{"name": "Step1", },
                 {"name": "Step2", }]

        self.hips_runner.build_steps_queue(que, steps, False)

        # assert
        self.assertEqual(2, resolve_hips_dependency.call_count)  # 2 times resolved
        self.assertEqual(2, _get_args.call_count)  # 2 times arguments resolved
        self.assertEqual(2, create_hips_run_script_standalone.call_count)  # 2 times standalone script created
        create_hips_run_collection_script.assert_not_called()
        run_queue.assert_not_called()

        # result
        res_que = Queue()
        res_que.put("runScriptStandalone")
        res_que.put("runScriptStandalone")

        self.assertEqual(res_que.qsize(), que.qsize())
        self.assertEqual(res_que.get(), que.get(block=False))
        self.assertEqual(res_que.get(), que.get(block=False))

    @patch('hips.core.controller.run_manager.load')
    def test_build_steps_queue_parent(self, load_mock):
        self.active_hips.parent = "aParent"

        # mock
        load_mock.return_value = self.active_hips

        resolve_hips_dependency = MagicMock(return_value={"path": "aPath"})
        self.test_catalog_collection.resolve_hips_dependency = resolve_hips_dependency

        create_hips_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.hips_runner.create_hips_run_collection_script = create_hips_run_collection_script

        create_hips_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.hips_runner.create_hips_run_script_standalone = create_hips_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.hips_runner._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.hips_runner.run_queue = run_queue

        # call
        self.hips_runner.catalog_collection = self.test_catalog_collection
        que = Queue()
        steps = [{"name": "Step1", },
                 {"name": "Step2", }]

        self.hips_runner.build_steps_queue(que, steps, False)

        # assert
        self.assertEqual(4, resolve_hips_dependency.call_count)  # 4 times resolved, 2 times step, 2 times step parent
        self.assertEqual(0, _get_args.call_count)  # 0 times arguments resolved
        self.assertEqual(0, create_hips_run_script_standalone.call_count)  # 0 times standalone script created
        create_hips_run_collection_script.assert_called_once_with({
            "parent_script_path": "aPath",
            "steps_hips": [self.active_hips, self.active_hips],
            "steps": steps
        })
        run_queue.assert_not_called()

        # result
        res_que = Queue()
        res_que.put("runScriptCollection")

        self.assertEqual(res_que.qsize(), que.qsize())
        self.assertEqual(res_que.get(), que.get(block=False))

    @patch('hips.core.controller.run_manager.load')
    def test_build_steps_queue_run_immediately(self, load_mock):
        # mock
        load_mock.return_value = self.active_hips

        resolve_hips_dependency = MagicMock(return_value={"path": "aPath"})
        self.test_catalog_collection.resolve_hips_dependency = resolve_hips_dependency

        create_hips_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.hips_runner.create_hips_run_collection_script = create_hips_run_collection_script

        create_hips_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.hips_runner.create_hips_run_script_standalone = create_hips_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.hips_runner._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.hips_runner.run_queue = run_queue

        # call
        self.hips_runner.catalog_collection = self.test_catalog_collection
        que = Queue()
        steps = [{"name": "Step1", }]

        self.hips_runner.build_steps_queue(que, steps, True)

        # assert
        self.assertEqual(1, resolve_hips_dependency.call_count)  # 1 times resolved
        self.assertEqual(1, _get_args.call_count)  # 1 times arguments resolved
        self.assertEqual(1, create_hips_run_script_standalone.call_count)  # 1 times standalone script created
        create_hips_run_collection_script.assert_not_called()
        self.assertEqual(2, run_queue.call_count)  # once to immediately run, once to clear que

    @patch('hips.core.controller.run_manager.create_script', return_value=None)
    def test_create_hips_run_script_standalone_no_run(self, create_script_mock):
        with self.assertRaises(ValueError):
            self.hips_runner.create_hips_run_script_standalone(self.active_hips, [])

        create_script_mock.assert_not_called()

    @patch('hips.core.controller.run_manager.create_script', return_value="aScript")
    def test_create_hips_run_script_standalone(self, create_script_mock):
        self.active_hips.run = print

        r = self.hips_runner.create_hips_run_script_standalone(self.active_hips, [])

        self.assertEqual([self.active_hips, ["aScript"]], r)
        create_script_mock.assert_called_once_with(self.active_hips, "\nget_active_hips().run()\n", [])

    @patch('hips.core.controller.run_manager.create_script', return_value="aScript")
    def test_create_hips_run_script_standalone_run_and_close(self, create_script_mock):
        self.active_hips.run = print
        self.active_hips.close = print

        r = self.hips_runner.create_hips_run_script_standalone(self.active_hips, [])

        self.assertEqual([self.active_hips, ["aScript"]], r)
        create_script_mock.assert_called_once_with(
            self.active_hips, "\nget_active_hips().run()\n\nget_active_hips().close()\n", []
        )

    @patch('hips.core.controller.run_manager.load')
    def test_create_hips_run_with_parent_script_standalone(self, load_mock):
        self.active_hips.parent = {"name": "aParent"}

        # mock
        load_mock.return_value = self.active_hips

        resolve_hips_dependency = MagicMock(return_value={"path": "aPath"})
        self.test_catalog_collection.resolve_hips_dependency = resolve_hips_dependency

        create_hips_run_with_parent_scrip = MagicMock(return_value="aScript")
        self.hips_runner.create_hips_run_with_parent_scrip = create_hips_run_with_parent_scrip

        resolve_args = MagicMock(return_value=["parent_args", "active_hips_args"])
        self.hips_runner.resolve_args = resolve_args

        # call
        self.hips_runner.catalog_collection = self.test_catalog_collection
        r = self.hips_runner.create_hips_run_with_parent_script_standalone(self.active_hips, [])

        # assert
        resolve_args.assert_called_once_with(self.active_hips, [self.active_hips], [None], [])
        create_hips_run_with_parent_scrip.assert_called_once_with(
            self.active_hips, "parent_args", [self.active_hips], "active_hips_args"
        )

        # result
        self.assertEqual([self.active_hips, "aScript"], r)

    @patch('hips.core.controller.run_manager.load')
    def test_create_hips_run_collection_script(self, load_mock):
        # mock
        load_mock.return_value = self.active_hips

        resolve_args = MagicMock(return_value=["parent_args", "active_hips_args"])
        self.hips_runner.resolve_args = resolve_args

        create_hips_run_with_parent_scrip = MagicMock(return_value="aScript")
        self.hips_runner.create_hips_run_with_parent_scrip = create_hips_run_with_parent_scrip

        # prepare
        self.active_hips.parent = {"name": "aParent"}
        p = {
            "parent_script_path": "aPathToaParent",
            "steps_hips": [self.active_hips, self.active_hips],
            "steps": ["step1", "step2"]
        }

        # call
        r = self.hips_runner.create_hips_run_collection_script(p)

        # assert
        resolve_args.assert_called_once_with(self.active_hips, [self.active_hips, self.active_hips], ["step1", "step2"])
        create_hips_run_with_parent_scrip.assert_called_once_with(
            self.active_hips, "parent_args", [self.active_hips, self.active_hips], "active_hips_args"
        )

        # result
        self.assertEqual([self.active_hips, "aScript"], r)

    @patch('hips.core.controller.run_manager.create_script')
    def test_create_hips_run_with_parent_scrip(self, create_script_mock):
        create_script_mock.side_effect = ["script_paretn", "script_child_1", "script_child_2"]

        r = self.hips_runner.create_hips_run_with_parent_scrip(
            self.active_hips, [], [self.active_hips, self.active_hips], [[], []]
        )

        # assert
        calls = [
            call(self.active_hips, "\nget_active_hips().run()\n", []),
            call(self.active_hips,
                 "\nmodule_logger().info(\"Started tsn\")\n\nget_active_hips().run()\n\nmodule_logger().info(\"Finished tsn\")\n\npop_active_hips()\n",
                 []),
            call(self.active_hips,
                 "\nmodule_logger().info(\"Started tsn\")\n\nget_active_hips().run()\n\nmodule_logger().info(\"Finished tsn\")\n\npop_active_hips()\n",
                 []),
        ]
        self.assertEqual(3, create_script_mock.call_count)
        create_script_mock.assert_has_calls(calls)

        # result
        self.assertEqual(["script_paretn", "script_child_1", "script_child_2", "\npop_active_hips()\n"], r)

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

        # hips object and arguments of the first hip solution mentioned in the steps above
        step1_hips = self.active_hips
        step1_hips.parent = {
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
        step1_hips.args = [
            {
                "name": "arg1_step1",
                "value": "arg1val_step1"
            }, {
                "name": "arg2_step1",
                "value": "arg2val_step1"
            }
        ]

        #  hips object and arguments of the second hip solution mentioned in the steps above
        step2_hips = deepcopy(self.active_hips)
        step2_hips.parent = {
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
        step2_hips.args = [
            {
                "name": "arg1_step2",
                "value": "arg1val_step2"
            }, {
                "name": "arg2_step2",
                "value": "arg2val_step2"
            }
        ]

        # the parent hip of both and its argument
        parent_hips = deepcopy(self.active_hips)
        parent_hips.args = [{
            "name": "parent_arg1",
            "default": "",
            "description": "",
        }, {
            "name": "parent_arg2",
            "default": "",
            "description": "",
        }]

        parsed_parent_args, parsed_steps_args_list = self.hips_runner.resolve_args(
            parent_hips,
            [step1_hips, step2_hips],
            steps
        )

        self.assertEqual(['', '--parent_arg1=parent_arg1_value', '--parent_arg2=parent_arg2_value'], parsed_parent_args)
        self.assertEqual([['', '--s1_arg1=s1_arg1_value'], ['', '--s2_arg1=s2_arg1_value']], parsed_steps_args_list)

    @patch('hips_runner.logging.configure_logging', return_value=None)
    @patch('hips_runner.logging.pop_active_logger', return_value=None)
    def test__run_in_environment_with_own_logger(self, pop_mock, conf_mock):
        class TestEnvironment:
            @staticmethod
            def run_scripts(script):
                return script

        self.active_hips.environment = TestEnvironment()

        self.hips_runner._run_in_environment_with_own_logger(self.active_hips, "")

        conf_mock.assert_called_once_with(LogLevel(0), self.active_hips["name"])

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

        r = self.hips_runner._get_args(step)

        self.assertEqual(["", "--test1=test1Value", "--test2=test2Value"], r)


if __name__ == '__main__':
    unittest.main()
