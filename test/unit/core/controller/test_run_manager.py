import unittest
from copy import deepcopy
from queue import Queue
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.run_manager import SolutionCollection, RunManager
from album.core.model.resolve_result import ResolveResult
from album.core.model.script_queue_entry import ScriptQueueEntry
from album.runner.core.concept.script_creator import ScriptCreatorRun
from album.runner.core.model.solution import Solution
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestRunManager(TestUnitCommon):
    def setUp(self):
        super().setUp()
        """Setup things necessary for all tests of this class"""
        album = self.create_album_test_instance()
        self.create_test_solution_no_env()
        album.run_manager()
        self.run_manager: RunManager = album._run_manager
        self.collection_manager = album.collection_manager()

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
        self.collection_manager.resolve_require_installation_and_load = resolve_installed_and_load

        with open(self.closed_tmp_file.name, mode="w") as f:
            f.write("A valid solution file!")

        _run = MagicMock(return_value=None)
        self.run_manager._run = _run

        # call
        self.run_manager.run(self.closed_tmp_file.name)

        # assert
        _run.assert_called_once_with(resolve_installed_and_load.return_value, False, None)
        resolve_installed_and_load.assert_called_once_with(self.closed_tmp_file.name)

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
        self.run_manager._run(ResolveResult("", None, None, None, self.active_solution), False)

        # assert
        build_queue.assert_called_once()
        run_queue.assert_called_once()

    def test_build_queue_steps_list(self):
        self.active_solution._setup.steps = [["step1A", "step1B"], "step2"]

        # mocks
        build_steps_queue = MagicMock(return_value=None)
        self.run_manager._build_steps_queue = build_steps_queue

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        create_solution_run_with_parent_script_standalone = MagicMock(return_value=None)
        self.run_manager._create_solution_run_with_parent_script_standalone = create_solution_run_with_parent_script_standalone

        create_solution_run_script_standalone = MagicMock(return_value=None)
        self.run_manager._create_solution_run_script_standalone = create_solution_run_script_standalone

        # call
        que = Queue()
        self.run_manager.build_queue(self.active_solution, None,
                                     que, ScriptCreatorRun(), run_immediately=False)

        # assert
        self.assertEqual(2, build_steps_queue.call_count)

        run_queue.assert_not_called()
        create_solution_run_with_parent_script_standalone.assert_not_called()
        create_solution_run_script_standalone.assert_not_called()

    def test_build_queue_steps_single(self):
        # mocks
        build_steps_queue = MagicMock(return_value=None)
        self.run_manager._build_steps_queue = build_steps_queue

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        create_solution_run_with_parent_script_standalone = MagicMock(return_value=None)
        self.run_manager._create_solution_run_with_parent_script_standalone = create_solution_run_with_parent_script_standalone

        create_solution_run_script_standalone = MagicMock(return_value=None)
        self.run_manager._create_solution_run_script_standalone = create_solution_run_script_standalone

        # call
        que = Queue()
        self.run_manager.build_queue(self.active_solution, None, que, ScriptCreatorRun(), run_immediately=False)

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
        que.put(ScriptQueueEntry(self.active_solution.coordinates(), ["test"], None))
        que.put(ScriptQueueEntry(self.active_solution.coordinates(), ["test2"], None))
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
                coordinates=self.active_solution.coordinates()
            )
        )
        self.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager._create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager._create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        que = Queue()
        steps = [{"name": "Step1", "group": "grp", "version": "v1"},
                 {"name": "Step2", "group": "grp", "version": "v1"}]

        self.run_manager._build_steps_queue(que, steps, ScriptCreatorRun(), False, [
            None])  # [None] mocks the namespace object from argument parsing of the parent

        # assert
        self.assertEqual(2, resolve_require_installation_and_load.call_count)  # 2 steps
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
        self.active_solution._setup.dependencies = {"parent": {"name": "aParent", "group": "grp", "version": "v1"}}

        # mocks
        catalog = EmptyTestClass()
        catalog.id = lambda: "niceId"

        resolve_require_installation_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPathChild",
                catalog=catalog,
                loaded_solution=self.active_solution,
                coordinates=self.active_solution.coordinates(),
                collection_entry=None
            )
        )
        self.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        resolve_require_installation = MagicMock(
            return_value=ResolveResult(
                path="aPathParent",
                catalog=catalog,
                loaded_solution=self.active_solution,
                coordinates=self.active_solution.coordinates(),
                collection_entry=None
            )
        )
        self.collection_manager.resolve_require_installation = resolve_require_installation

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager._create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager._create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        que = Queue()
        steps = [{"name": "Step1", "group": "grp", "version": "v1"},
                 {"name": "Step2", "group": "grp", "version": "v1"}]
        scr = ScriptCreatorRun()
        self.run_manager._build_steps_queue(que, steps, scr, False, [
            None])  # [None] mocks the namespace object from argument parsing of the parent

        # assert
        self.assertEqual(2, resolve_require_installation_and_load.call_count)  # 2 times step
        self.assertEqual(2, resolve_require_installation.call_count)  # 2 times parent
        self.assertEqual(0, _get_args.call_count)  # 0 times arguments resolved
        self.assertEqual(0, create_solution_run_script_standalone.call_count)  # 0 times standalone script created

        r1 = create_solution_run_collection_script.call_args_list[0][0][0]

        r2 = SolutionCollection(parent_parsed_args=[None], parent_script_path="aPathParent",
                                        parent_script_catalog=catalog,
                                        steps_solution=[self.active_solution, self.active_solution], steps=steps)
        p1 = r1.parent_script_path
        p2 = r2.parent_script_path
        create_solution_run_collection_script.assert_called_once_with(
            r2,
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
                coordinates=self.active_solution.coordinates()
            )
        )
        self.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        create_solution_run_collection_script = MagicMock(return_value="runScriptCollection")
        self.run_manager._create_solution_run_collection_script = create_solution_run_collection_script

        create_solution_run_script_standalone = MagicMock(return_value="runScriptStandalone")
        self.run_manager._create_solution_run_script_standalone = create_solution_run_script_standalone

        _get_args = MagicMock(return_value=None)
        self.run_manager._get_args = _get_args

        run_queue = MagicMock(return_value=None)
        self.run_manager.run_queue = run_queue

        # call
        que = Queue()
        steps = [{"name": "Step1", "group": "grp", "version": "v1"}]

        self.run_manager._build_steps_queue(que, steps, ScriptCreatorRun(), True, [None])

        # assert
        self.assertEqual(1, resolve_require_installation_and_load.call_count)  # 1 tep resolved
        self.assertEqual(1, _get_args.call_count)  # 1 times arguments resolved
        self.assertEqual(1, create_solution_run_script_standalone.call_count)  # 1 times standalone script created
        create_solution_run_collection_script.assert_not_called()
        self.assertEqual(2, run_queue.call_count)  # once to immediately run, once to clear que

    def test_create_solution_run_script_standalone(self):
        script_creator = ScriptCreatorRun()
        create_script = MagicMock(return_value="myscript")
        script_creator.create_script = create_script

        set_environment = MagicMock(return_value=None)
        self.album.environment_manager().set_environment = set_environment

        r = self.run_manager._create_solution_run_script_standalone(self.active_solution, None, [], script_creator)

        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual(["myscript"], r.scripts)
        create_script.assert_called_once()
        set_environment.assert_called_once()

    @unittest.skip("TODO fix implementation")
    def test_create_solution_run_script_standalone_run_and_close(self):
        # TODO this is not actually assigning run or close to the solution and also not checking for it.
        script_creator = ScriptCreatorRun()
        create_script = MagicMock(return_value="myscript")
        script_creator.create_script = create_script

        set_environment = MagicMock(return_value=None)
        self.album.environment_manager().set_environment = set_environment

        r = self.run_manager._create_solution_run_script_standalone(self.active_solution, None, [], script_creator)

        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual(["myscript"], r.scripts)
        set_environment.assert_called_once()

    def test_create_solution_run_with_parent_script_standalone(self):
        self.active_solution._setup.dependencies = {"parent": {"name": "aParent", "group": "grp", "version": "v1"}}

        # mock
        catalog = self.collection_manager.catalogs().get_local_catalog()
        resolve_require_installation_and_load = MagicMock(
            return_value=ResolveResult(
                path="aPath",
                catalog=catalog,
                loaded_solution=self.active_solution,
                collection_entry=None,
                coordinates=self.active_solution.coordinates()
            )
        )
        self.collection_manager.resolve_require_installation_and_load = resolve_require_installation_and_load

        create_solution_run_with_parent_script = MagicMock(return_value="aScript")
        self.run_manager._create_solution_run_with_parent_script = create_solution_run_with_parent_script

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.run_manager._resolve_args = resolve_args

        set_environment = MagicMock(return_value=None)
        self.album.environment_manager().set_environment = set_environment

        scr = ScriptCreatorRun()

        # call
        r = self.run_manager._create_solution_run_with_parent_script_standalone(
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
        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual("aScript", r.scripts)

    @patch('album.core.controller.state_manager.StateManager.load')
    @patch('album.core.controller.collection.solution_handler.SolutionHandler.set_cache_paths')
    def test_create_solution_run_collection_script(self, set_cache_paths_mock, load_mock):
        # mock
        load_mock.return_value = self.active_solution
        catalog = EmptyTestClass()
        catalog._name = lambda: "niceName"

        resolve_args = MagicMock(return_value=["parent_args", "active_solution_args"])
        self.run_manager._resolve_args = resolve_args

        create_solution_run_with_parent_script = MagicMock(return_value="aScript")
        self.run_manager._create_solution_run_with_parent_script = create_solution_run_with_parent_script

        set_environment = MagicMock(return_value=EmptyTestClass())
        self.album.environment_manager().set_environment = set_environment

        # prepare
        self.active_solution._setup.dependencies = {"parent": {"name": "aParent"}}
        p = SolutionCollection(
            parent_parsed_args=[None],
            parent_script_path="aPathToaParent",
            parent_script_catalog=catalog,
            steps_solution=[self.active_solution, self.active_solution],
            steps=["step1", "step2"]
        )

        scr = ScriptCreatorRun()
        # call
        r = self.run_manager._create_solution_run_collection_script(p, scr)

        # assert
        resolve_args.assert_called_once_with(
            parent_solution=self.active_solution,
            steps_solution=[self.active_solution, self.active_solution],
            steps=["step1", "step2"],
            step_solution_parsed_args=[None]
        )
        create_solution_run_with_parent_script.assert_called_once_with(
            self.active_solution,
            "parent_args",
            [self.active_solution, self.active_solution],
            "active_solution_args",
            scr
        )
        set_environment.assert_called_once()

        # result
        self.assertEqual(self.active_solution.coordinates(), r.coordinates)
        self.assertEqual("aScript", r.scripts)
        self.assertEqual(set_environment.return_value, r.environment)
        set_cache_paths_mock.assert_called_once()

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
        step1_solution._setup.dependencies = {
            'parent': {
                'name': 'app1',
                'args': [
                    {
                        'name': 'parent_arg1',
                        'value': 'parent_arg1_value'
                    },
                    {
                        'name': 'parent_arg2',
                        'value': 'parent_arg2_value'
                    }
                ]
            }
        }
        # Todo: the arguments of the step description contradict with the one the step1 one actually needs!!!
        step1_solution._setup.args = [
            {
                'name': 'arg1_step1',
                'value': 'arg1val_step1'
            }, {
                'name': 'arg2_step1',
                'value': 'arg2val_step1'
            }
        ]

        # solution object and arguments of the second solution mentioned in the steps above
        step2_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        step2_solution._setup.dependencies = {
            'parent': {
                'name': 'app1',
                'args': [
                    {
                        'name': 'parent_arg1',
                        'value': 'parent_arg1_contradicting_value_with_other_definition!'
                    },
                    {
                        'name': 'parent_arg2',
                        'value': 'parent_arg2_value'
                    }
                ]
            }
        }

        step2_solution._setup.args = [
            {
                'name': 'arg1_step2',
                'value': 'arg1val_step2'
            }, {
                'name': 'arg2_step2',
                'value': 'arg2val_step2'
            }
        ]

        # the parent solution of both and its argument
        parent_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        parent_solution._setup.args = [{
            'name': 'parent_arg1',
            'default': '',
            'description': '',
        }, {
            'name': 'parent_arg2',
            'default': '',
            'description': '',
        }]

        parsed_parent_args, parsed_steps_args_list = self.run_manager._resolve_args(
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
        run_scripts_mock = MagicMock()
        self.album.environment_manager().run_scripts = run_scripts_mock

        environment = EmptyTestClass()
        environment.name = lambda: ""

        self.run_manager._run_in_environment_with_own_logger(ScriptQueueEntry(self.active_solution.coordinates(), [""], environment))

        conf_mock.assert_called_once_with(self.active_solution.coordinates().name())
        run_scripts_mock.assert_called_once_with(environment, [""])
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
