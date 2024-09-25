import argparse
import json
import sys
from importlib.metadata import version as importlib_version
from pathlib import Path
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

        env_variables = {}  # os.environ.copy()
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

        script_path = collection_solution.loaded_solution().script()

        # handle old runner API versions, here, solution_action is not available via API, it is set via a script line
        if collection_solution.loaded_solution().setup().album_api_version < "0.6.0":
            module_logger().warning(
                "You are using an old version of the album runner API within your solution. "
                "Consider updating your solution if possible."
            )
            script_path = ScriptManager._handle_old_runner_api_version(
                collection_solution, solution_action, args
            )

        return ScriptQueueEntry(
            collection_solution.coordinates(),
            script_path,
            solution_action,
            args,
            environment=environment,
            solution_installation_path=installation_path,
            solution_package_path=package_path,
        )

    @staticmethod
    def _handle_old_runner_api_version(
        collection_solution: ICollectionSolution,
        solution_action: ISolution.Action,
        args: List[str],
    ) -> Path:
        # build script the in the old way and give it to the environment manager for execution
        solution_wrapper_content = ScriptManager._create_script_content(
            collection_solution.loaded_solution(), solution_action, args
        )

        # write the script to a temporary file
        script_path = (
            collection_solution.loaded_solution().installation().internal_cache_path()
            / "solution_wrapper.py"
        )
        with open(script_path, "w") as f:
            f.write(solution_wrapper_content)

        return script_path

    @staticmethod
    def _get_execution_block(
        solution_object: ISolution, solution_action: ISolution.Action
    ) -> str:
        # no installation allowed for old API versions
        if solution_action == ISolution.Action.UNINSTALL:
            return ScriptManager._get_uninstall_block()
        if solution_action == ISolution.Action.RUN:
            return ScriptManager._get_run_block(solution_object)
        if solution_action == ISolution.Action.TEST:
            return ScriptManager._get_test_block(solution_object)
        raise ValueError("Unknown solution action!")

    @staticmethod
    def _get_uninstall_block() -> str:
        return "\nget_active_solution().setup().uninstall()\n"

    @staticmethod
    def _get_run_block(solution_object: ISolution, pop_solution: bool = False) -> str:
        execution_block = (
            '\nget_active_logger().info("Starting %s")\n' % solution_object.setup().name
        )
        if solution_object.setup().run and callable(solution_object.setup().run):
            execution_block += "\nget_active_solution().setup().run()\n"
        else:
            get_active_logger().warn(
                'No "run" routine configured for solution "%s".'
                % solution_object.setup().name
            )

        if solution_object.setup().close and callable(solution_object.setup().close):
            execution_block += "\nget_active_solution().setup().close()\n"

        execution_block += (
            '\nget_active_logger().info("Finished %s")\n' % solution_object.setup().name
        )

        if pop_solution:
            execution_block += "\npop_active_solution()\n"

        return execution_block

    @staticmethod
    def _get_test_block(solution_object: ISolution) -> str:
        if "pre_test" in solution_object.setup():
            execution_block = "\nd = get_active_solution().setup().pre_test()\n"
            execution_block += "d = {} if d is None else d\n"  # noqa: P103
        else:
            execution_block = "\nd = {}\n"  # noqa: P103
        execution_block += '\nsys.argv = sys.argv + ["=".join([c, d[c]]) for c in d]\n'

        # parse args again after pre_test() routine if necessary.
        if "args" in solution_object.setup().keys():
            execution_block += "\nget_active_solution().set_args(parser.parse_args())\n"

        execution_block += ScriptManager._get_run_block(solution_object)
        execution_block += "\nget_active_solution().setup().test()\n"

        return execution_block

    @staticmethod
    def _create_script_content(
        solution_object: ISolution,
        solution_action: ISolution.Action,
        arguments: List[str],
    ) -> str:
        # add the album script
        with open(solution_object.script()) as f:
            solution_script = f.read()

        script = solution_script
        script += "\n"
        script += ScriptManager._create_header(arguments)

        # API access
        script += ScriptManager._api_access(solution_object)

        if solution_object.setup().args:
            script += ScriptManager._append_arguments(
                solution_object.setup().args, solution_object
            )

        # append execution block
        script += ScriptManager._get_execution_block(solution_object, solution_action)

        return script

    @staticmethod
    def _create_header(arguments: List[str]) -> str:
        header = (
            "import sys\n"
            "import json\n"
            "import argparse\n"
            "import time\n"
            "from album.runner.api import *\n"
            "from album.runner.album_logging import configure_logging, LogLevel, get_active_logger\n"
        )
        # create logging
        header += (
            'configure_logging("script", loglevel=%s, stream_handler=sys.stdout, '
            % (album_logging.to_loglevel(album_logging.get_loglevel_name()))
            + 'formatter_string="'
            + "%(levelname)-7s %(name)s - %(message)s"
            + '")\n'
        )
        # This could have an issue with nested quotes
        get_active_logger().debug(
            "Add sys.argv arguments to runtime script: %s..." % ", ".join(arguments)
        )
        header += "sys.argv = json.loads(r'%s')\n" % json.dumps(arguments)

        return header

    @staticmethod
    def _api_access(solution_object: ISolution) -> str:
        enc = sys.getfilesystemencoding()

        # mapping from internal paths to API paths for the user
        script = "album_runner_init("
        script += (
            "environment_path="
            + "{!r}".format(
                str(solution_object.installation().environment_path()).encode(enc)
            )
            + ", "
        )
        script += 'environment_name="" , '
        script += (
            "data_path="
            + "{!r}".format(str(solution_object.installation().data_path()).encode(enc))
            + ", "
        )
        script += (
            "package_path="
            + "{!r}".format(
                str(solution_object.installation().package_path()).encode(enc)
            )
            + ", "
        )
        script += (
            "app_path="
            + "{!r}".format(str(solution_object.installation().app_path()).encode(enc))
            + ", "
        )
        script += (
            "user_cache_path="
            + "{!r}".format(
                str(solution_object.installation().user_cache_path()).encode(enc)
            )
            + ", "
        )
        script += "internal_cache_path=" + "{!r}".format(
            str(solution_object.installation().internal_cache_path()).encode(enc)
        )
        script += ")\n"
        return script

    @staticmethod
    def _append_arguments(args, solution_object: ISolution) -> str:
        script = ""
        get_active_logger().debug(
            "Read out arguments in album solution and add to runtime script..."
        )
        # special argument parsing cases
        if isinstance(args, str):
            ScriptManager._handle_args_string(args)
        else:
            script += ScriptManager._handle_args_list(args, solution_object)
        return script

    @staticmethod
    def _handle_args_string(args):
        # pass through to module
        if args == "pass-through":
            get_active_logger().info(
                "Argument parsing not specified in album solution. Passing arguments through..."
            )
        else:
            message = "Argument keyword '%s' not supported!" % args
            get_active_logger().error(message)
            raise argparse.ArgumentError(argument=args, message=message)

    @staticmethod
    def _handle_args_list(args, solution_object):
        get_active_logger().debug(
            "Add argument parsing for album solution to runtime script..."
        )
        # Add the argument handling
        script = (
            "\nparser = argparse.ArgumentParser(description='album run %s')\n"
            % solution_object.setup().name
        )
        script += ScriptManager._str_to_bool_str()
        for arg in args:
            if "action" in arg.keys():
                script += ScriptManager._create_action_class_string(arg)
            script += ScriptManager._create_parser_argument_string(arg)
        script += "\nget_active_solution().set_args(parser.parse_args())\n"
        return script

    @staticmethod
    def _str_to_bool_str():
        return """def strtobool (val):
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))
    """

    @staticmethod
    def _create_parser_argument_string(arg):
        keys = arg.keys()

        if "default" in keys and "action" in keys:
            get_active_logger().warning(
                "Default values cannot be automatically set when an action is provided! "
                "Ignoring default values..."
            )

        parse_arg = "parser.add_argument('--%s', " % arg["name"]
        if "default" in keys:
            if "type" in keys and arg["type"] == "boolean":
                parse_arg += "default=%s, " % arg["default"]
            else:
                parse_arg += "default='%s', " % arg["default"]
        if "description" in keys:
            parse_arg += "help='%s', " % arg["description"]
        if "type" in keys:
            parse_arg += "type=%s, " % ScriptManager._parse_type(arg["type"])
        if "required" in keys:
            parse_arg += (
                "required=%s, " % arg["required"]
            )  # CAUTION: no ''! Boolean value
        if "action" in keys:
            class_name = ScriptManager._get_action_class_name(arg["name"])
            parse_arg += (
                "action=%s, " % class_name
            )  # CAUTION: no ''! action must be callable!
        parse_arg += ")\n"

        return parse_arg

    @staticmethod
    def _create_action_class_string(arg):
        class_name = ScriptManager._get_action_class_name(arg["name"])
        return """
class {class_name}(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super({class_name}, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, get_active_solution().get_arg(self.dest)['action'](values))

""".format(
            class_name=class_name
        )

    @staticmethod
    def _get_action_class_name(name):
        class_name = "%sAction" % name.capitalize()
        return class_name

    @staticmethod
    def _parse_type(type_str):
        if type_str == "string":
            return "str"
        if type_str == "file":
            return "Path"
        if type_str == "directory":
            return "Path"
        if type_str == "integer":
            return "int"
        if type_str == "float":
            return "float"
        if type_str == "boolean":
            return "strtobool"

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

        env_variables = {}  # os.environ.copy()
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
