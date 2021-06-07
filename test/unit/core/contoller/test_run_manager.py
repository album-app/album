import unittest
from copy import deepcopy
from pathlib import Path
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
            self.hips_runner = RunManager()
            init_mock.assert_called_once()

    def tearDown(self) -> None:
        super().tearDown()

    @patch('hips.core.controller.run_manager.load')
    def test_run(self, load_mock):
        # mocks
        load_mock.return_value = self.active_hips

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        resolve_from_str = MagicMock(return_value={"path": Path(self.closed_tmp_file.name), "catalog": None})
        self.config.resolve_from_str = resolve_from_str

        _run = MagicMock(return_value=None)
        self.hips_runner._run = _run

        self.hips_runner.catalog_configuration = self.config

        # test
        self.hips_runner.run(self.closed_tmp_file.name)

        # assert
        _run.assert_called_once_with(self.active_hips)
        load_mock.assert_called_once_with(Path(self.closed_tmp_file.name))

    def test__run_steps_list(self):
        self.active_hips.steps = [["step1A", "step1B"], "step2"]

        # mocks
        run_single_step = MagicMock(return_value=None)
        self.hips_runner.run_single_step = run_single_step

        run_steps = MagicMock(return_value=None)
        self.hips_runner.run_steps = run_steps

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner._run(self.active_hips)

        self.assertEqual(2, run_steps.call_count)
        run_steps.assert_has_calls([call(["step1A", "step1B"]), call(["step2"])])

        run_single_step.assert_not_called()

    def test__run_steps_single(self):
        self.hips_runner.catalog_configuration = self.config

        # mocks
        run_single_step = MagicMock(return_value=None)
        self.hips_runner.run_single_step = run_single_step

        run_steps = MagicMock(return_value=None)
        self.hips_runner.run_steps = run_steps

        self.hips_runner._run(self.active_hips)

        run_steps.assert_not_called()

        run_single_step.assert_called_once()

    @patch('hips.core.controller.run_manager.load')
    def test_run_steps_single_step(self, load_mock):
        steps = [{"name": "Step1"}]

        # mocks
        run_single_step = MagicMock(return_value=None)
        self.hips_runner.run_single_step = run_single_step

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": self.closed_tmp_file.name, "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        load_mock.return_value = self.active_hips

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner.run_steps(steps)

        run_single_step.assert_called_once_with(self.active_hips, [""])
        load_mock.assert_called_once_with(self.closed_tmp_file.name)

    @patch('hips.core.controller.run_manager.load')
    def test_run_steps_parent(self, load_mock):
        steps = [{"name": "Step1", "parent": "aParent"}]
        self.active_hips.parent = "aParent"

        # mocks
        run_single_step = MagicMock(return_value=None)
        self.hips_runner.run_single_step = run_single_step

        run_and_empty_queue = MagicMock(return_value=None)
        self.hips_runner.run_and_empty_queue = run_and_empty_queue

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": self.closed_tmp_file.name, "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        load_mock.return_value = self.active_hips

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner.run_steps(steps)

        load_mock.assert_called_once_with(self.closed_tmp_file.name)
        run_and_empty_queue.assert_called_once_with({
            "parent_script_path": self.closed_tmp_file.name,
            "steps_hips": [self.active_hips],
            "steps": [steps[0]]
        })
        run_single_step.assert_not_called()

    @patch('hips.core.controller.run_manager.load')
    def test_run_steps_parents(self, load_mock):
        steps = [{"name": "Step1", "parent": "aParent"}, {"name": "Step2", "parent": "aParent"}]
        self.active_hips.parent = "sameParent"

        # mocks
        run_single_step = MagicMock(return_value=None)
        self.hips_runner.run_single_step = run_single_step

        run_and_empty_queue = MagicMock(return_value=None)
        self.hips_runner.run_and_empty_queue = run_and_empty_queue

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": self.closed_tmp_file.name, "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        load_mock.return_value = self.active_hips

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner.run_steps(steps)

        load_mock.assert_has_calls([call(self.closed_tmp_file.name), call(self.closed_tmp_file.name)])
        run_and_empty_queue.assert_called_once_with({
            "parent_script_path": self.closed_tmp_file.name,
            "steps_hips": [self.active_hips, self.active_hips],
            "steps": [steps[0], steps[1]]
        })
        run_single_step.assert_not_called()

    @patch('hips.core.controller.run_manager.create_hips_with_parent_script', return_value=None)
    @patch('hips.core.controller.run_manager.load')
    def test_run_hips_collection(self, load_mock, create_script_mock):
        # mocks
        same_parent_steps = {
            "parent_script_path": "aPath",
            "steps_hips": [self.active_hips, self.active_hips],
            "steps": [[{"1": 1}], {"2": 2}]
        }
        load_mock.return_value = self.active_hips

        resolve_args = MagicMock(return_value=["argsParent", "argsChild"])
        self.hips_runner.resolve_args = resolve_args

        _run_in_environment_with_own_logger = MagicMock(return_value=None)
        self.hips_runner._run_in_environment_with_own_logger = _run_in_environment_with_own_logger

        # test
        self.hips_runner.run_hips_collection(same_parent_steps)

        # assert
        _run_in_environment_with_own_logger.assert_called_once_with(self.active_hips, None)
        resolve_args.assert_called_once_with(
            self.active_hips,
            same_parent_steps["steps_hips"],
            same_parent_steps["steps"]
        )
        create_script_mock.assert_called_once()

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

    @patch('hips.core.controller.run_manager.load')
    def test_run_single_step(self, load_mock):
        self.active_hips["parent"] = {"name": "aNiceParent"}

        self.hips_runner.catalog_configuration = self.config

        # mocks
        resolve_args = MagicMock(return_value=["argsParent", "argsChild"])
        self.hips_runner.resolve_args = resolve_args

        run_steps_with_parent = MagicMock(return_value=None)
        self.hips_runner.run_steps_with_parent = run_steps_with_parent

        run_single_step_standalone = MagicMock(return_value=None)
        self.hips_runner.run_single_step_standalone = run_single_step_standalone

        resolve_hips_dependency = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        # test
        self.hips_runner.run_single_step(self.active_hips, None)

        # assert
        run_single_step_standalone.assert_not_called()
        run_steps_with_parent.assert_called_once()
        load_mock.assert_called_once()
        resolve_args.assert_called_once()

    def test_run_single_step_parent(self):
        # mocks
        run_steps_with_parent = MagicMock(return_value=None)
        self.hips_runner.run_steps_with_parent = run_steps_with_parent

        run_single_step_standalone = MagicMock(return_value=None)
        self.hips_runner.run_single_step_standalone = run_single_step_standalone

        # test
        self.hips_runner.run_single_step(self.active_hips, None)

        # assert
        run_single_step_standalone.assert_called_once()
        run_steps_with_parent.assert_not_called()

    @unittest.skip("Script like routine. Testing unnecessary!")
    def test_run_single_step_standalone(self):
        pass

    @unittest.skip("Script like routine. Testing unnecessary!")
    def test_run_steps_with_parent(self):
        pass

    @patch('hips_runner.logging.configure_logging', return_value=None)
    @patch('hips_runner.logging.pop_active_logger', return_value=None)
    def test__run_in_environment_with_own_logger(self, pop_mock, conf_mock):
        class TestEnvironment:
            @staticmethod
            def run_script(script):
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
