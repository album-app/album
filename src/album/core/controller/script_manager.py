import argparse
import os
from importlib.metadata import version as importlib_version
from queue import Empty, Queue
from typing import Any, Dict, List, Optional, Tuple

from album.runner import album_logging
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution
from album.runner.core.default_values_runner import DefaultValuesRunner
from packaging import version

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.script_manager import IScriptManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.core.model.script_queue_entry import ScriptQueueEntry
from album.core.utils.operations.solution_operations import get_parent_dict

module_logger = get_active_logger


class ScriptManager(IScriptManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def run_solution_script(
        self, resolve_result: ICollectionSolution, solution_action: ISolution.Action
    ):
        queue: Queue = Queue()
        self.build_queue(resolve_result, queue, solution_action, False, [""])
        script_queue_entry = queue.get(block=False)

        env_variables = os.environ.copy()
        env_variables[
            DefaultValuesRunner.env_variable_action.value
        ] = script_queue_entry.solution_action.name
        env_variables[DefaultValuesRunner.env_variable_installation.value] = str(
            script_queue_entry.solution_installation_path
        )
        env_variables[DefaultValuesRunner.env_variable_package.value] = str(
            script_queue_entry.solution_package_path
        )
        env_variables[DefaultValuesRunner.env_variable_environment.value] = str(
            script_queue_entry.environment.path()
        )
        env_variables[DefaultValuesRunner.env_variable_logger_level.value] = str(
            album_logging.get_loglevel_name()
        )

        self.album.environment_manager().run_script(
            script_queue_entry.environment,
            script_queue_entry.script,
            pipe_output=False,
            argv=script_queue_entry.args,
            environment_variables=env_variables,
        )

    def run_queue(self, queue: Queue):
        module_logger().debug("Running queue...")
        try:
            while True:
                script_queue_entry = queue.get(block=False)
                module_logger().debug(
                    'Running task "%s"...' % script_queue_entry.coordinates.name()
                )
                self._run_in_environment(script_queue_entry)
                module_logger().debug(
                    'Finished running task "%s"!'
                    % script_queue_entry.coordinates.name()
                )
                queue.task_done()
        except Empty:
            module_logger().debug("Currently nothing more to run!")

    def build_queue(
        self,
        collection_solution: ICollectionSolution,
        queue: Queue,
        solution_action: ISolution.Action,
        run_immediately: bool = False,
        argv: Optional[List[str]] = None,
    ) -> None:
        if argv is None:
            argv = [""]
        solution = collection_solution.loaded_solution()

        parent = get_parent_dict(solution)
        if parent:
            module_logger().debug("Adding standalone solution with parent to queue...")
            # create script with parent
            queue.put(
                self._create_solution_run_with_parent_script_standalone(
                    collection_solution, argv, solution_action
                )
            )
        else:
            module_logger().debug("Adding standalone to queue...")
            # create script without parent
            queue.put(
                self._create_solution_run_script_standalone(
                    collection_solution, argv, solution_action
                )
            )

    def _create_solution_run_script_standalone(
        self,
        collection_solution: ICollectionSolution,
        args: List[str],
        solution_action: ISolution.Action,
    ) -> ScriptQueueEntry:
        module_logger().debug(
            'Creating standalone album script "%s"...'
            % collection_solution.coordinates().name()
        )

        self._print_credit([collection_solution.loaded_solution()])
        environment = self.album.environment_manager().set_environment(
            collection_solution
        )
        installation_path = (
            collection_solution.loaded_solution().installation().installation_path()
        )
        package_path = (
            collection_solution.loaded_solution().installation().package_path()
        )

        # check if album core solution API < solution API
        solution_api_version = (
            collection_solution.loaded_solution().setup()["album_api_version"]
            if "album_api_version" in collection_solution.loaded_solution().setup()
            else DefaultValues.runner_api_package_version.value
        )

        core_version = importlib_version(DefaultValues.runner_api_package_name.value)

        if version.parse(core_version) < version.parse(solution_api_version):
            module_logger().warning(
                f"Solution API version {solution_api_version} is higher than the album core solution API version"
                f" {core_version}. Consider updating your album installation."
            )

        return ScriptQueueEntry(
            collection_solution.coordinates(),
            collection_solution.loaded_solution().script(),
            solution_action,
            args,
            environment=environment,
            solution_installation_path=installation_path,
            solution_package_path=package_path,
        )

    def _create_solution_run_with_parent_script_standalone(
        self,
        collection_solution: ICollectionSolution,
        args: List[str],
        solution_action: ISolution.Action,
    ) -> ScriptQueueEntry:
        environment = self.album.environment_manager().set_environment(
            collection_solution
        )
        active_solution = collection_solution.loaded_solution()

        # TODO this should probably move into the runner
        self._print_credit([active_solution])

        return ScriptQueueEntry(
            collection_solution.loaded_solution().coordinates(),
            collection_solution.loaded_solution().script(),
            solution_action,
            args,
            environment,
            active_solution.installation().installation_path(),
            active_solution.installation().package_path(),
        )

    def __parse_args(self, active_solution: ISolution, args: List[str]):
        parser = argparse.ArgumentParser()

        class FileAction(argparse.Action):
            def __init__(self, option_strings, dest, nargs=None, **kwargs):
                if nargs is not None:
                    raise ValueError("nargs not allowed")
                super().__init__(option_strings, dest, **kwargs)

            def __call__(self, p, namespace, values, option_string=None):
                setattr(
                    namespace,
                    self.dest,
                    active_solution.get_arg(self.dest)["action"](values),
                )

        for element in active_solution.setup()["args"]:
            if "action" in element.keys():
                parser.add_argument("--" + element["name"], action=FileAction)
            else:
                parser.add_argument("--" + element["name"])

        return parser.parse_known_args(args=args)

    def _resolve_args(
        self,
        parent_solution: ISolution,
        steps_solution: List[ISolution],
        steps: List[Dict[str, Any]],
        step_solution_parsed_args: List[argparse.Namespace],
        args=None,
    ) -> Tuple[List[str], List[List[str]]]:
        args = [] if args is None else args
        parsed_parent_args: List[str] = []
        parsed_steps_args_list = []

        module_logger().debug("Parsing arguments...")

        # iterate over all steps and parse arguments together
        for idx, step_solution in enumerate(steps_solution):
            step_parser = argparse.ArgumentParser()

            # the steps description
            step = steps[idx]

            if step:  # case steps argument resolving
                step_args = self._get_args(step, step_solution_parsed_args[0])
            else:  # case single step solution
                step_args = args

            # add parent arguments to the step album object arguments
            parent_dict = get_parent_dict(step_solution)
            if parent_dict:
                if "args" in parent_dict:
                    for param in parent_dict["args"]:
                        step_args.insert(0, f"--{param['name']}={str(param['value'])}")

            # add parent arguments
            if "args" in parent_solution.setup():
                [
                    step_parser.add_argument("--" + element["name"])
                    for element in parent_solution.setup()["args"]
                ]

            # parse all known arguments
            args_known, args_unknown = step_parser.parse_known_args(step_args)

            # only set parents args if not already set
            if not parsed_parent_args:
                parsed_parent_args = [""]
                parsed_parent_args.extend(
                    [
                        "--" + arg_name + "=" + getattr(args_known, arg_name)
                        for arg_name in vars(args_known)
                    ]
                )
                module_logger().debug(
                    'For step "%s" set parent arguments to %s...'
                    % (step_solution.coordinates().name(), parsed_parent_args)
                )

            # args_unknown are step args
            parsed_steps_args_list.append(args_unknown)
            module_logger().debug(
                'For step "%s" set step arguments to %s...'
                % (step_solution.coordinates().name(), args_unknown)
            )

        return parsed_parent_args, parsed_steps_args_list

    def _run_in_environment(self, script_queue_entry: ScriptQueueEntry) -> None:
        module_logger().debug(
            'Running script in environment of solution "%s"...'
            % script_queue_entry.coordinates.name()
        )

        env_variables = os.environ.copy()
        env_variables[
            DefaultValuesRunner.env_variable_action.value
        ] = script_queue_entry.solution_action.name
        env_variables[DefaultValuesRunner.env_variable_installation.value] = str(
            script_queue_entry.solution_installation_path
        )
        env_variables[DefaultValuesRunner.env_variable_package.value] = str(
            script_queue_entry.solution_package_path
        )
        env_variables[DefaultValuesRunner.env_variable_environment.value] = str(
            script_queue_entry.environment.path()
        )
        env_variables[DefaultValuesRunner.env_variable_logger_level.value] = str(
            album_logging.get_loglevel_name()
        )

        self.album.environment_manager().run_script(
            script_queue_entry.environment,
            str(script_queue_entry.script),
            argv=script_queue_entry.args,
            environment_variables=env_variables,
        )
        module_logger().debug(
            'Done running script in environment of solution "%s"...'
            % script_queue_entry.coordinates.name()
        )

    @staticmethod
    def _get_args(step: Dict[str, Any], args: argparse.Namespace) -> List[str]:
        argv = [""]
        if "args" in step:
            for param in step["args"]:
                argv.append(f"--{param['name']}={str(param['value'](args))}")
        return argv

    @staticmethod
    def _print_credit(active_solutions: List[ISolution]) -> None:
        res = ScriptManager._get_credit_as_string(active_solutions)
        if res:
            module_logger().info(res)

    @staticmethod
    def _get_credit_as_string(active_solutions: List[ISolution]) -> Optional[str]:
        res = ""
        for active_solution in active_solutions:
            if active_solution.setup().cite:
                for citation in active_solution.setup().cite:
                    text = citation["text"]
                    if "doi" in citation:
                        text += " (DOI: %s)" % citation["doi"]
                    res += "%s\n" % text
        if len(res) > 0:
            return "\n\nSolution credits:\n\n%s\n" % res
        return None
