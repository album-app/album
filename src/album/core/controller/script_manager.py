import argparse
import os
import platform
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from album.runner import album_logging
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution
from album.runner.core.default_values_runner import DefaultValuesRunner

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.script_manager import IScriptManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.core.model.script_queue_entry import ScriptQueueEntry

module_logger = get_active_logger


class ScriptManager(IScriptManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def run_solution_script(
        self,
        resolve_result: ICollectionSolution,
        solution_action: ISolution.Action,
        pipe_output: bool = True,
    ) -> None:
        queue: Queue = Queue()
        self.build_queue(resolve_result, queue, solution_action, False, [""])
        self.run_queue(queue, pipe_output=pipe_output)

    def run_queue(self, queue: Queue, pipe_output: bool = True) -> None:
        module_logger().debug("Running queue...")
        try:
            while True:
                script_queue_entry = queue.get(block=False)
                module_logger().debug(
                    'Running task "%s"...' % script_queue_entry.coordinates.name()
                )
                self._run_in_environment(script_queue_entry, pipe_output=pipe_output)
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
        module_logger().debug("Adding standalone to queue...")
        queue.put(
            self._create_solution_script(collection_solution, argv, solution_action)
        )
        module_logger().debug("Added standalone to queue.")

    def _create_solution_script(
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

        # check if album core solution API < solution API
        solution_api_version = (
            collection_solution.loaded_solution().setup()["album_api_version"]
            if "album_api_version" in collection_solution.loaded_solution().setup()
            else DefaultValues.runner_api_package_version.value
        )

        _ = self.album.migration_manager().is_core_api_outdated(solution_api_version)
        _ = self.album.migration_manager().is_solution_api_outdated(
            solution_api_version
        )

        # manage backwards compatibility when necessary
        script_path = (
            ScriptManager._handle_old_runner_api_version(collection_solution)
            if self.album.migration_manager().is_migration_needed_solution_api(
                solution_api_version
            )
            else collection_solution.loaded_solution().script()
        )

        return ScriptQueueEntry(
            collection_solution.coordinates(),
            script_path,
            solution_action,
            args,
            environment=self.album.environment_manager().set_environment(
                collection_solution
            ),
            solution_installation_path=collection_solution.loaded_solution()
            .installation()
            .installation_path(),
            solution_package_path=collection_solution.loaded_solution()
            .installation()
            .package_path(),
        )

    @staticmethod
    def _handle_old_runner_api_version(
        collection_solution: ICollectionSolution,
    ) -> Path:
        script_path = (
            collection_solution.loaded_solution().installation().internal_cache_path()
            / "solution_wrapper.py"
        )
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))

        with open(script_path, "w") as f:
            # write the backup script
            f.write(
                Path(current_path)
                .joinpath("..", "utils", "runner", "backwards_compatibility_0_6_1.py")
                .read_text()
            )
            # write the solution script
            f.write(
                'exec(open(r"%s").read())'
                % collection_solution.loaded_solution().script()
            )

        return script_path

    def _run_in_environment(
        self, script_queue_entry: ScriptQueueEntry, pipe_output: bool = True
    ) -> None:
        module_logger().debug(
            'Running script in environment of solution "%s"...'
            % script_queue_entry.coordinates.name()
        )

        # todo: on windows necessary to work - on linux not
        env_variables = {}
        if platform.system() == "Windows":
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
            pipe_output=pipe_output,
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
