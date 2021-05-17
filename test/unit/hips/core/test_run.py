import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, call
from unittest.mock import patch

from hips.core.model.logging import LogLevel
from hips.core.run import HipsRunner
from test.unit.test_common import TestHipsCommon


class TestHipsRun(TestHipsCommon):
    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.create_test_config()
        self.create_test_hips_no_env()

        with patch.object(HipsRunner, '__init__', return_value=None) as init_mock:
            self.hips_runner = HipsRunner()
            init_mock.assert_called_once()

    @patch('hips.core.run.load')
    @patch('hips.core.run.HipsRunner._run', return_value=None)
    def test_run(self, run_mock, load_mock):
        class Args:
            def __init__(self, p):
                self.path = p

        load_mock.return_value = self.active_hips

        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, 'w') as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_from_str = MagicMock(return_value={"path": Path(tmp_file.name), "catalog": None})
        self.config.resolve_from_str = resolve_from_str

        self.hips_runner.catalog_configuration = self.config
        self.hips_runner.run(Args(tmp_file.name))

        run_mock.assert_called_once_with(self.active_hips)
        load_mock.assert_called_once_with(Path(tmp_file.name))

    @patch('hips.core.run.HipsRunner.run_single_step', return_value=None)
    @patch('hips.core.run.HipsRunner.run_steps', return_value=None)
    def test__run_steps_list(self, steps_mock, run_single_step_mock):
        self.active_hips.steps = [["step1A", "step1B"], "step2"]

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner._run(self.active_hips)

        self.assertEqual(2, steps_mock.call_count)
        steps_mock.assert_has_calls([call(["step1A", "step1B"]), call(["step2"])])

        run_single_step_mock.assert_not_called()

    @patch('hips.core.run.HipsRunner.run_single_step', return_value=None)
    @patch('hips.core.run.HipsRunner.run_steps', return_value=None)
    def test__run_steps_single(self, steps_mock, run_single_step_mock):
        self.hips_runner.catalog_configuration = self.config

        self.hips_runner._run(self.active_hips)

        steps_mock.assert_not_called()

        run_single_step_mock.assert_called_once()

    @patch('hips.core.run.load')
    @patch('hips.core.run.HipsRunner.run_single_step', return_value=None)
    def test_run_steps_single_step(self, run_single_step_mock, load_mock):
        steps = [{"name": "Step1"}]

        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, 'w') as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": tmp_file.name, "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        load_mock.return_value = self.active_hips

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner.run_steps(steps)

        run_single_step_mock.assert_called_once_with(self.active_hips, [""])
        load_mock.assert_called_once_with(tmp_file.name)

    @patch('hips.core.run.HipsRunner.run_and_empty_queue', return_value=None)
    @patch('hips.core.run.load')
    @patch('hips.core.run.HipsRunner.run_single_step', return_value=None)
    def test_run_steps_parent(self, run_single_step_mock, load_mock, run_and_empty_queue_mock):
        steps = [{"name": "Step1", "parent": "aParent"}]
        self.active_hips.parent = "aParent"

        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, 'w') as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": tmp_file.name, "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        load_mock.return_value = self.active_hips

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner.run_steps(steps)

        load_mock.assert_called_once_with(tmp_file.name)
        run_and_empty_queue_mock.assert_called_once_with({
            "parent_script_path": tmp_file.name,
            "steps_hips": [self.active_hips],
            "steps": [steps[0]]
        })
        run_single_step_mock.assert_not_called()

    @patch('hips.core.run.HipsRunner.run_and_empty_queue', return_value=None)
    @patch('hips.core.run.load')
    @patch('hips.core.run.HipsRunner.run_single_step', return_value=None)
    def test_run_steps_parents(self, run_single_step_mock, load_mock, run_and_empty_queue_mock):
        steps = [{"name": "Step1", "parent": "aParent"}, {"name": "Step2", "parent": "aParent"}]
        self.active_hips.parent = "sameParent"

        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, 'w') as f:
            f.write("A valid solution file!")

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": tmp_file.name, "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        load_mock.return_value = self.active_hips

        self.hips_runner.catalog_configuration = self.config

        self.hips_runner.run_steps(steps)

        load_mock.assert_has_calls([call(tmp_file.name), call(tmp_file.name)])
        run_and_empty_queue_mock.assert_called_once_with({
            "parent_script_path": tmp_file.name,
            "steps_hips": [self.active_hips, self.active_hips],
            "steps": [steps[0], steps[1]]
        })
        run_single_step_mock.assert_not_called()

    @patch('hips.core.run.HipsRunner.resolve_args', return_value=["argsParent", "argsChild"])
    @patch('hips.core.run.create_hips_with_parent_script', return_value=None)
    @patch('hips.core.run.load')
    @patch('hips.core.run.HipsRunner._run_in_environment_with_own_logger')
    def test_run_hips_collection(self, run_env_mock, load_mock, create_script_mock, resolve_args_mock):
        same_parent_steps = {
            "parent_script_path": "aPath",
            "steps_hips": [self.active_hips, self.active_hips],
            "steps": [[{"1": 1}], {"2": 2}]
        }
        load_mock.return_value = self.active_hips

        self.hips_runner.run_hips_collection(same_parent_steps)

        run_env_mock.assert_called_once_with(self.active_hips, None)
        resolve_args_mock.assert_called_once_with(
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

    @patch('hips.core.run.load')
    @patch('hips.core.run.HipsRunner.resolve_args', return_value=["argsParent", "argsChild"])
    @patch('hips.core.run.HipsRunner.run_steps_with_parent', return_value=None)
    @patch('hips.core.run.HipsRunner.run_single_step_standalone', return_value=None)
    def test_run_single_step_parent(self, run_alone_mock, run_parent_mock, load_mock, resolve_mock):
        self.active_hips["parent"] = "aNiceParent"

        # overwrite resolving with mock
        resolve_hips_dependency = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        self.hips_runner.run_single_step(self.active_hips, None)

        run_alone_mock.assert_not_called()
        run_parent_mock.assert_called_once()
        load_mock.assert_called_once()
        resolve_mock.assert_called_once()

    @patch('hips.core.run.HipsRunner.run_steps_with_parent', return_value=None)
    @patch('hips.core.run.HipsRunner.run_single_step_standalone', return_value=None)
    def test_run_single_step_parent(self, run_alone_mock, run_parent_mock):
        self.hips_runner.run_single_step(self.active_hips, None)

        run_alone_mock.assert_called_once()
        run_parent_mock.assert_not_called()

    @unittest.skip("Script like routine. Testing unnecessary!")
    def test_run_single_step_standalone(self):
        pass

    @unittest.skip("Script like routine. Testing unnecessary!")
    def test_run_steps_with_parent(self):
        pass

    @patch('hips.core.model.logging.configure_logging', return_value=None)
    @patch('hips.core.model.logging.pop_active_logger', return_value=None)
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
