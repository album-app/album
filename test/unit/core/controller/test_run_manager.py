import unittest
from copy import deepcopy
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.run_manager import RunManager, SolutionCollection
from album.core.model.resolve_result import ResolveResult
from album.runner.concept.script_creator import ScriptCreatorRun
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestRunManager(TestUnitCommon):
    def setUp(self):
        super().setUp()
        """Setup things necessary for all tests of this class"""
        self.create_album_test_instance()
        self.create_test_solution_no_env()
        self.run_manager = RunManager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_run(self):
        # mocks
        catalog = self.collection_manager.catalogs().get_local_catalog()

        resolve_installed_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPath",
                catalog=catalog,
                loaded_solution=self.active_solution,
                collection_entry=None,
                coordinates=self.active_solution.coordinates
            )
        )
        self.run_manager.collection_manager.resolve_require_installation_and_load = resolve_installed_and_load

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        _run = MagicMock(return_value=None)
        self.run_manager._run = _run

        _resolve_installed = MagicMock(
            return_value=ResolveResult(
                path=Path(self.closed_tmp_file.name),
                catalog=catalog,
                collection_entry=None,
                coordinates=None
            )
        )

        self.run_manager.collection_manager._resolve_installed = _resolve_installed

        set_environment = MagicMock(return_value=None)
        self.run_manager.environment_manager.set_environment = set_environment

        # call
        self.run_manager.run(self.closed_tmp_file.name)

        # assert
        _run.assert_called_once_with(self.active_solution, False, None)
        resolve_installed_and_load.assert_called_once_with(self.closed_tmp_file.name)
        set_environment.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_run_from_catalog_coordinates(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_run_from_coordinates(self):
        # TODO implement
        pass

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

    def test_build_steps_queue_no_parent(self):
        # mock
        catalog = self.collection_manager.catalogs().get_local_catalog()
        resolve_require_installation_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPath",
                catalog=catalog,
                loaded_solution=self.active_solution,
                collection_entry=None,
                coordinates=self.active_solution.coordinates
            )
        )
        self.run_manager.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager.create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        set_environment = MagicMock(return_value=None)
        self.run_manager.environment_manager.set_environment = set_environment

        # call
        que = Queue()
        steps = [{"name": "Step1", "group": "grp", "version": "v1"},
                 {"name": "Step2", "group": "grp", "version": "v1"}]

        self.run_manager.build_steps_queue(que, steps, ScriptCreatorRun(), False, [
            None])  # [None] mocks the namespace object from argument parsing of the parent

        # assert
        self.assertEqual(2, resolve_require_installation_and_load.call_count)  # 2 steps
        self.assertEqual(2, _get_args.call_count)  # 2 times arguments resolved
        self.assertEqual(2, create_solution_run_script_standalone.call_count)  # 2 times standalone script created
        self.assertEqual(2, set_environment.call_count)  # 2 times environment set

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
        self.active_solution.parent = {"name": "aParent", "group": "grp", "version": "v1"}

        # mocks
        catalog = EmptyTestClass()
        catalog.id = "niceId"

        resolve_require_installation_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPathChild",
                catalog=catalog,
                loaded_solution=self.active_solution,
                coordinates=self.active_solution.coordinates,
                collection_entry=None
            )
        )
        self.run_manager.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        resolve_require_installation = MagicMock(
            return_value=ResolveResult(
                path="aPathParent",
                catalog=catalog,
                loaded_solution=self.active_solution,
                coordinates=self.active_solution.coordinates,
                collection_entry=None
            )
        )
        self.run_manager.collection_manager.resolve_require_installation = resolve_require_installation

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager.create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        set_env_mock = MagicMock()
        self.run_manager.environment_manager.set_environment = set_env_mock

        # call
        que = Queue()
        steps = [{"name": "Step1", "group": "grp", "version": "v1"},
                 {"name": "Step2", "group": "grp", "version": "v1"}]
        scr = ScriptCreatorRun()
        self.run_manager.build_steps_queue(que, steps, scr, False, [
            None])  # [None] mocks the namespace object from argument parsing of the parent

        # assert
        self.assertEqual(2, resolve_require_installation_and_load.call_count)  # 2 times step
        self.assertEqual(2, resolve_require_installation.call_count)  # 2 times parent
        self.assertEqual(2, set_env_mock.call_count)  # 2 times step environment set
        self.assertEqual(0, _get_args.call_count)  # 0 times arguments resolved
        self.assertEqual(0, create_solution_run_script_standalone.call_count)  # 0 times standalone script created

        create_solution_run_collection_script.assert_called_once_with(
            SolutionCollection(
                parent_parsed_args=[None],
                parent_script_path="aPathParent",
                parent_script_catalog=catalog,
                steps_solution=[self.active_solution, self.active_solution],
                steps=steps
            ),
            scr
        )
        run_queue.assert_not_called()

        # result
        res_que = Queue()
        res_que.put("runScriptCollection")

        self.assertEqual(res_que.qsize(), que.qsize())
        self.assertEqual(res_que.get(), que.get(block=False))

    def test_build_steps_queue_run_immediately(self):
        # mock
        catalog = self.collection_manager.catalogs().get_local_catalog()

        resolve_require_installation_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPath",
                catalog=catalog,
                loaded_solution=self.active_solution,
                collection_entry=None,
                coordinates=self.active_solution.coordinates
            )
        )
        self.run_manager.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager.create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager.create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        set_environment = MagicMock(return_value=None)
        self.run_manager.environment_manager.set_environment = set_environment

        # call
        que = Queue()
        steps = [{"name": "Step1", "group": "grp", "version": "v1"}]

        self.run_manager.build_steps_queue(que, steps, ScriptCreatorRun(), True, [None])

        # assert
        self.assertEqual(1, resolve_require_installation_and_load.call_count)  # 1 tep resolved
        self.assertEqual(1, _get_args.call_count)  # 1 times arguments resolved
        self.assertEqual(1, create_solution_run_script_standalone.call_count)  # 1 times standalone script created
        self.assertEqual(1, set_environment.call_count)  # 1 time environment set
        create_solution_run_collection_script.assert_not_called()
        self.assertEqual(2, run_queue.call_count)  # once to immediately run, once to clear que

    def test_create_solution_run_script_standalone_no_run(self):
        script_creator = ScriptCreatorRun()

        with self.assertRaises(ValueError):
            self.run_manager.create_solution_run_script_standalone(self.active_solution, [], script_creator)

    def test_create_solution_run_script_standalone(self):
        self.active_solution.run = print

        script_creator = ScriptCreatorRun()
        create_script = MagicMock(return_value="myscript")
        script_creator.create_script = create_script

        r = self.run_manager.create_solution_run_script_standalone(self.active_solution, [], script_creator)

        self.assertEqual([self.active_solution, ["myscript"]], r)
        create_script.assert_called_once()

    def test_create_solution_run_script_standalone_run_and_close(self):
        script_creator = ScriptCreatorRun()
        create_script = MagicMock(return_value="myscript")
        script_creator.create_script = create_script

        r = self.run_manager.create_solution_run_script_standalone(self.active_solution, [], script_creator)

        self.assertEqual([self.active_solution, ["myscript"]], r)

    def test_create_solution_run_with_parent_script_standalone(self):
        self.active_solution.parent = {"name": "aParent", "group": "grp", "version": "v1"}

        # mock
        catalog = self.collection_manager.catalogs().get_local_catalog()
        resolve_require_installation_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPath",
                catalog=catalog,
                loaded_solution=self.active_solution,
                collection_entry=None,
                coordinates=self.active_solution.coordinates
            )
        )
        self.run_manager.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        create_solution_run_with_parent_script = MagicMock(return_value="aScript")
        self.run_manager.create_solution_run_with_parent_script = create_solution_run_with_parent_script

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.run_manager.resolve_args = resolve_args

        set_environment = MagicMock(return_value=None)
        self.run_manager.environment_manager.set_environment = set_environment

        scr = ScriptCreatorRun()

        # call
        r = self.run_manager.create_solution_run_with_parent_script_standalone(
            self.active_solution, [], scr
        )

        # assert
        resolve_args.assert_called_once_with(
            parent_solution=self.active_solution,
            steps_solution=[self.active_solution],
            steps=[None],
            step_solution_parsed_args=[None],
            args=[]
        )
        create_solution_run_with_parent_script.assert_called_once_with(
            self.active_solution, "parent_args", [self.active_solution], "active_solution_args", scr
        )
        resolve_require_installation_and_load.assert_called_once()
        set_environment.assert_called_once()

        # result
        self.assertEqual([self.active_solution, "aScript"], r)

    @patch('album.core.controller.run_manager.load')
    def test_create_solution_run_collection_script(self, load_mock):
        # mock
        load_mock.return_value = self.active_solution
        catalog = EmptyTestClass()
        catalog.name = "niceName"

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.run_manager.resolve_args = resolve_args

        create_solution_run_with_parent_scrip = MagicMock(return_value="aScript")
        self.run_manager.create_solution_run_with_parent_script = create_solution_run_with_parent_scrip

        set_environment = MagicMock(return_value=None)
        self.run_manager.environment_manager.set_environment = set_environment

        # prepare
        self.active_solution.parent = {"name": "aParent"}
        p = SolutionCollection(
            parent_parsed_args=[None],
            parent_script_path="aPathToaParent",
            parent_script_catalog=catalog,
            steps_solution=[self.active_solution, self.active_solution],
            steps=["step1", "step2"]
        )

        scr = ScriptCreatorRun()
        # call
        r = self.run_manager.create_solution_run_collection_script(p, scr)

        # assert
        resolve_args.assert_called_once_with(
            parent_solution=self.active_solution,
            steps_solution=[self.active_solution, self.active_solution],
            steps=["step1", "step2"],
            step_solution_parsed_args=[None]
        )
        create_solution_run_with_parent_scrip.assert_called_once_with(
            self.active_solution,
            "parent_args",
            [self.active_solution, self.active_solution],
            "active_solution_args",
            scr
        )
        set_environment.assert_called_once()

        # result
        self.assertEqual([self.active_solution, "aScript"], r)

    @unittest.skip("Needs to be implemented!")
    def test_create_solution_run_with_parent_script(self):
        # ToDo: implement!
        pass

    def test_resolve_args(self):
        # the arguments of the steps solution for each step
        steps = [
            {
                'name': 'Step1',
                'args': [{'name': 's1_arg1', 'value': lambda args: 's1_arg1_value'}]
            },
            {
                'name': 'Step2',
                'args': [{'name': 's2_arg1', 'value': lambda args: 's2_arg1_value'}]
            }
        ]

        # solution object and arguments of the first solution mentioned in the steps above
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
                'name': 'arg1_step1',
                'value': 'arg1val_step1'
            }, {
                'name': 'arg2_step1',
                'value': 'arg2val_step1'
            }
        ]

        # solution object and arguments of the second solution mentioned in the steps above
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
                'name': 'arg1_step2',
                'value': 'arg1val_step2'
            }, {
                'name': 'arg2_step2',
                'value': 'arg2val_step2'
            }
        ]

        # the parent solution of both and its argument
        parent_solution = deepcopy(self.active_solution)
        parent_solution.args = [{
            'name': 'parent_arg1',
            'default': '',
            'description': '',
        }, {
            'name': 'parent_arg2',
            'default': '',
            'description': '',
        }]

        parsed_parent_args, parsed_steps_args_list = self.run_manager.resolve_args(
            parent_solution,
            [step1_solution, step2_solution],
            steps,
            [None],  # mocks the namespace object from the argument parsing of the parent
            args=None
        )

        self.assertEqual(['', '--parent_arg1=parent_arg1_value', '--parent_arg2=parent_arg2_value'], parsed_parent_args)
        self.assertEqual([['', '--s1_arg1=s1_arg1_value'], ['', '--s2_arg1=s2_arg1_value']], parsed_steps_args_list)

    @patch('album.runner.album_logging.configure_logging', return_value=None)
    @patch('album.runner.album_logging.pop_active_logger', return_value=None)
    def test__run_in_environment_with_own_logger(self, pop_mock, conf_mock):
        e = EmptyTestClass()
        self.active_solution.environment = e

        run_scripts_mock = MagicMock()
        self.run_manager.environment_manager.run_scripts = run_scripts_mock

        self.run_manager._run_in_environment_with_own_logger(self.active_solution, "")

        conf_mock.assert_called_once_with(self.active_solution.coordinates.name)
        run_scripts_mock.assert_called_once_with(self.active_solution, "")
        pop_mock.assert_called_once()

    def test__get_args(self):
        step = {
            "args": [
                {
                    "name": "test1",
                    "value": lambda args: "test1Value"
                },
                {
                    "name": "test2",
                    "value": lambda args: "test2Value"
                }
            ]
        }

        r = self.run_manager._get_args(step, None)

        self.assertEqual(["", "--test1=test1Value", "--test2=test2Value"], r)


if __name__ == '__main__':
    unittest.main()
