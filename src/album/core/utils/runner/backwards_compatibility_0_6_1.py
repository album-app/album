"""This module provides backwards compatibility for the album script API."""
# NOTE: DO NOT IMPORT ANY MODULES FROM album IN THIS FILE
import argparse
import logging
import os
import sys
import threading
from abc import ABCMeta, abstractmethod  # necessary import
from enum import Enum  # necessary import
from enum import unique
from pathlib import Path
from typing import List, Optional

# Global variable for tracking the currently active logger. Do not use this directly instead use get_active_logger()
_active_logger = {}

DEBUG = False


def thread_stack():
    """Return the stack of active loggers for the current thread."""
    global _active_logger
    thread_id = threading.current_thread().ident
    if thread_id not in _active_logger:
        _active_logger[thread_id] = []
    return _active_logger.get(thread_id)


def push_active_logger(logger):
    """Insert a logger to the _active_logger stack."""
    thread_stack().insert(0, logger)


def get_active_logger():
    """Return the currently active logger, which is defined globally."""
    stack = thread_stack()
    if len(stack) > 0:
        return stack[0]
    return logging.getLogger()  # root logger


def get_active_logger_in_thread(thread_ident):
    """Return the currently active logger, which is defined globally."""
    if thread_ident in _active_logger:
        stack = _active_logger.get(thread_ident)
        if len(stack) > 0:
            return stack[0]
    return logging.getLogger()  # root logger


def pop_active_logger():
    """Pop the currently active logger from the _active_solution stack."""
    stack = thread_stack()
    if len(stack) > 0:
        logger = stack.pop(0)
        logger.handlers.clear()
        return logger
    else:
        return logging.getLogger()  # root logger


@unique
class LogLevel(Enum):
    """LogLevel album allows.

    Notes:
        Only add Names available in python standard logging module.

    """

    DEBUG = 1
    INFO = 0
    WARNING = 2
    ERROR = 3


def to_loglevel(value):
    """Convert a string value to a @LogLevel.

    Args:
        value:
            The string value

    Returns:
        The LovLevel class enum

    Raises:
        KeyError when loglevel unknown.

    """
    try:
        return LogLevel[value]
    except KeyError as err:
        logger = get_active_logger()
        logger.error("Loglevel %s not allowed or unknown!" % value)
        raise err


def configure_logging(
    name,
    loglevel=None,
    stream_handler=None,
    formatter_string=None,
    parent_thread_id=None,
    parent_name=None,
):
    """Configure a logger with a certain name and loglevel.

        loglevel:
            The Loglevel to use. Either DEBUG or INFO.
        name:
            The name of the logger.

    Returns:
        The logger object.

    """
    # create or get currently active logger
    if parent_thread_id is None:
        parent = get_active_logger()
    else:
        parent = get_active_logger_in_thread(parent_thread_id)

    if not parent_name:
        parent_name = parent.name

    # if currently active logger has the same name, just return it
    if parent_name == name:
        return parent

    # make sure the new logger is registered as a child of the currently active logger in order to propagate logs
    if parent_name.endswith("." + name):
        name = parent_name
    else:
        if not name.startswith(parent_name + "."):
            name = parent_name + "." + name

    logger = logging.getLogger(name)
    if loglevel is None:
        logger.setLevel(parent.level)
    else:
        logger.setLevel(loglevel.name)

    if stream_handler:
        # create formatter
        if not formatter_string:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            formatter = logging.Formatter(formatter_string)
        # create console handler and set level to debug
        # ToDo: different handlers necessary? e.g. logging additional into a file?
        ch = logging.StreamHandler(stream_handler)
        ch.setLevel(loglevel.name)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    # push logger if not already active
    if get_active_logger() != logger:
        push_active_logger(logger)

    return logger


def get_loglevel():
    """Return the loglevel of the current active logger."""
    return get_active_logger().level


def get_loglevel_name():
    """Return the Name of the loglevel of the current active logger."""
    logger = get_active_logger()
    return logging.getLevelName(logger.level)


def set_loglevel(loglevel):
    """Set logLevel for a logger with a certain name for ALL available handlers.

    Args:
        loglevel:
            The Loglevel to use. Either DEBUG or INFO.

    """
    # logger loglevel
    active_logger = get_active_logger()
    active_logger.debug("Set loglevel to %s..." % loglevel.name)

    active_logger.setLevel(loglevel.name)

    # set handler loglevel
    for handler in active_logger.handlers:
        handler_name = (
            handler.stream.name
            if hasattr(handler, "stream")
            and hasattr(handler.stream, active_logger.name)
            else "default handler"
        )
        active_logger.debug(
            f"Set loglevel for handler {handler_name} to {loglevel.name}..."
        )
        handler.setLevel(loglevel.name)


class LogEntry:
    """Class for a log entry."""

    name = None
    level = None
    message = None

    def __init__(self, name, level, message):
        """Initialize the log entry with the given name, level, and message."""
        self.name = name
        self.level = level
        self.message = message


def debug_settings():
    """Return the debug settings."""
    return DEBUG


class ICoordinates:
    """Interface for the Coordinates of a solution."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def name(self):
        """Return the name of the coordinates."""
        raise NotImplementedError

    @abstractmethod
    def group(self):
        """Return the group of the coordinates."""
        raise NotImplementedError

    @abstractmethod
    def version(self):
        """Return the version of the coordinates."""
        raise NotImplementedError


class ISolution:
    """Interface for a album solution."""

    __metaclass__ = ABCMeta

    class Action(Enum):
        """The actions a solution can perform."""

        NO_ACTION = 0
        INSTALL = 1
        RUN = 2
        TEST = 3
        UNINSTALL = 4

    class ISetup(dict):
        """Interface for the setup of a solution."""

        __metaclass__ = ABCMeta
        __getattr__ = dict.get
        __setattr__ = dict.__setitem__
        __delattr__ = dict.__delitem__

    class IInstallation:
        """Interface for the installation of a solution."""

        __metaclass__ = ABCMeta

        @abstractmethod
        def environment_path(self) -> Path:
            """Return the environment path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def user_cache_path(self) -> Path:
            """Return the user cache path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def internal_cache_path(self) -> Path:
            """Return the internal cache path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def package_path(self) -> Path:
            """Return the package path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def data_path(self) -> Path:
            """Return the data path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def app_path(self) -> Path:
            """Return the app path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def installation_path(self) -> Path:
            """Return the installation path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def set_environment_path(self, path: Path):
            """Set the environment path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def set_package_path(self, package_path: Path):
            """Set the package path of the solution."""
            raise NotImplementedError

        @abstractmethod
        def set_installation_path(self, solution_base_path: Path):
            """Set the installation path of the solution."""
            raise NotImplementedError

    @abstractmethod
    def setup(self) -> ISetup:
        """Return the setup of the solution."""
        raise NotImplementedError

    @abstractmethod
    def installation(self) -> IInstallation:
        """Return the installation of the solution."""
        raise NotImplementedError

    @abstractmethod
    def coordinates(self) -> ICoordinates:
        """Return the coordinates of the solution."""
        raise NotImplementedError

    @abstractmethod
    def script(self) -> Path:
        """Return the script of the solution."""
        raise NotImplementedError

    @abstractmethod
    def args(self) -> List:
        """Return the arguments of the solution."""
        raise NotImplementedError

    @abstractmethod
    def get_arg(self, name: str):
        """Get a specific named argument for this album if it exists."""
        raise NotImplementedError

    @abstractmethod
    def get_identifier(self) -> str:
        """Return the identifier of the solution."""
        raise NotImplementedError

    @abstractmethod
    def set_script(self, script: str):
        """Set the script of the solution."""
        raise NotImplementedError

    @abstractmethod
    def set_args(self, args: List):
        """Set the arguments of the solution."""
        raise NotImplementedError


class DefaultValuesRunner(Enum):
    """Add an entry here to initialize default attributes for a album runner instance."""

    solution_app_prefix = "app"  # solution specific app files
    solution_data_prefix = "data"  # solution specific data files
    solution_internal_cache_prefix = (
        "icache"  # solution specific album internal cache files
    )
    solution_user_cache_prefix = (
        "ucache"  # solution specific user cache files, accessible via runner API
    )

    env_variable_action = "ALBUM_SOLUTION_ACTION"
    env_variable_logger_level = "ALBUM_LOGGER_LEVEL"
    env_variable_package = "ALBUM_SOLUTION_PACKAGE"
    env_variable_installation = "ALBUM_SOLUTION_INSTALLATION"
    env_variable_environment = "ALBUM_SOLUTION_ENVIRONMENT"


class Coordinates(ICoordinates):
    """Class for the Coordinates of a solution."""

    def __init__(self, group: str, name: str, version: str) -> None:
        """Initialize the coordinates with the given group, name, and version."""
        self._group = group
        self._name = name
        self._version = version

    def name(self):
        """Return the name of the coordinates."""
        return self._name

    def group(self):
        """Return the group of the coordinates."""
        return self._group

    def version(self):
        """Return the version of the coordinates."""
        return self._version

    def __str__(self) -> str:
        """Return a string representation of the coordinates."""
        return f"{self._group}:{self._name}:{self._version}"

    def __eq__(self, o: object) -> bool:
        """Check if two coordinates are equal."""
        return (
            isinstance(o, ICoordinates)
            and o.group() == self._group
            and o.name() == self._name
            and o.version() == self._version
        )

    def __hash__(self):
        """Return the hash of the coordinates."""
        return hash(self.__str__())


class Solution(ISolution):
    """Encapsulate an album solution configuration."""

    class Setup(ISolution.ISetup):
        """Encapsulate the setup of an album solution."""

        def __init__(self, attrs=None):
            """Set the attributes of the setup.

            Args:
                attrs:
                    Dictionary containing the attributes.
            """
            if attrs:
                super().__init__(attrs)
            else:
                super().__init__()

        def __str__(self, indent=2):
            """Return a string representation of the setup."""
            s = "\n"
            for attr in self.__dict__:
                for _ in range(0, indent):
                    s += "\t"
                s += (attr + ":\t" + str(getattr(self, attr))) + "\n"
            return s

    class Installation(ISolution.IInstallation):
        """Encapsulate the installation of an album solution."""

        def __init__(self):
            """Initialize the installation of the solution."""
            super().__init__()
            # API keywords
            self._installation_path = None
            self._environment_path = None
            self._package_path = None

        def environment_path(self) -> Path:
            """Return the environment path of the solution."""
            return self._environment_path

        def user_cache_path(self) -> Path:
            """Return the user cache path of the solution."""
            return self._installation_path.joinpath(
                DefaultValuesRunner.solution_user_cache_prefix.value
            )

        def internal_cache_path(self) -> Path:
            """Return the internal cache path of the solution."""
            return self._installation_path.joinpath(
                DefaultValuesRunner.solution_internal_cache_prefix.value
            )

        def package_path(self) -> Path:
            """Return the package path of the solution."""
            return self._package_path

        def installation_path(self) -> Path:
            """Return the installation path of the solution."""
            return self._installation_path

        def data_path(self) -> Path:
            """Return the data path of the solution."""
            return self._installation_path.joinpath(
                DefaultValuesRunner.solution_data_prefix.value
            )

        def app_path(self) -> Path:
            """Return the app path of the solution."""
            return self._installation_path.joinpath(
                DefaultValuesRunner.solution_app_prefix.value
            )

        def set_environment_path(self, path: Path):
            """Set the environment path of the solution."""
            self._environment_path = path

        def set_package_path(self, package_path: Path):
            """Set the package path of the solution."""
            self._package_path = package_path

        def set_installation_path(self, solution_base_path: Path):
            """Set the installation path of the solution."""
            self._installation_path = solution_base_path

    def __init__(self, attrs=None):
        """Initialize the solution with the given attributes."""
        self._installation = Solution.Installation()
        self._setup = Solution.Setup(attrs)
        self._coordinates = Coordinates(attrs["group"], attrs["name"], attrs["version"])
        self._args = None
        self._script = None

    def setup(self) -> ISolution.ISetup:
        """Return the setup of the solution."""
        return self._setup

    def installation(self) -> ISolution.IInstallation:
        """Return the installation of the solution."""
        return self._installation

    def coordinates(self) -> ICoordinates:
        """Return the coordinates of the solution."""
        return self._coordinates

    def script(self) -> Path:
        """Return the script of the solution."""
        return self._script

    def get_arg(self, k):
        """Get a specific named argument for this album if it exists."""
        matches = [arg for arg in self._setup.args if arg["name"] == k]
        return matches[0]

    def get_identifier(self) -> str:
        """Return the identifier of the solution."""
        identifier = "_".join(
            [self._setup.group, self._setup.name, self._setup.version]
        )
        return identifier

    def set_script(self, script: str):
        """Set the script of the solution."""
        self._script = script

    def __eq__(self, other):
        """Check if two solutions are equal."""
        return isinstance(other, Solution) and other.coordinates() == self._coordinates

    def set_args(self, args: List):
        """Set the arguments of the solution."""
        self._args = args

    def args(self) -> List:
        """Return the arguments of the solution."""
        return self._args


class SolutionScript:
    """This class provides a script API for album solutions."""

    @staticmethod
    def make_action(solution, mydest):
        """Make an action for the solution."""

        class CustomAction(argparse.Action):
            def __call__(self, parser, namespace, values, option_string=None):
                setattr(namespace, mydest, solution.get_arg(mydest)["action"](values))

        return CustomAction

    @staticmethod
    def get_script_logging_formatter_str():
        """Return the logging formatter string."""
        return "%(levelname)-7s %(name)s - %(message)s"

    @staticmethod
    def get_script_logging_formatter_regex():
        """Return the regex for the logging formatter."""
        regex_log_level = "DEBUG|INFO|WARNING|ERROR"
        return r"(%s)\s+([\s\S]+) - ([\s\S]+)?" % regex_log_level

    @staticmethod
    def trigger_solution_goal(
        solution,
        goal,
        package_path=None,
        installation_base_path=None,
        environment_path=None,
    ):
        """Trigger a goal for a solution."""
        SolutionScript.api_access(
            solution, package_path, installation_base_path, environment_path
        )
        parser = None
        if solution.setup().args:
            append_arguments = (goal == Solution.Action.RUN) or (
                goal == Solution.Action.TEST
            )
            if append_arguments:
                parser = SolutionScript.append_arguments(solution)
        if goal == Solution.Action.INSTALL:
            solution.setup().install()
        if goal == Solution.Action.UNINSTALL:
            solution.setup().uninstall()
        if goal == Solution.Action.RUN:
            SolutionScript.execute_run_action(solution)
        if goal == Solution.Action.TEST:
            if "pre_test" in solution.setup():
                d = solution.setup().pre_test()
            else:
                d = {}
            if d is None:
                d = {}
            sys.argv = sys.argv + ["=".join([c, d[c]]) for c in d]

            # parse args again after pre_test() routine if necessary.
            if parser and "args" in solution.setup().keys():
                args = parser.parse_args()
                solution.set_args(args)

            SolutionScript.execute_run_action(solution)
            solution.setup().test()

    @staticmethod
    def execute_run_action(solution):
        """Execute the run action of the solution."""
        get_active_logger().info("Starting %s" % solution.setup().name)
        if solution.setup().run and callable(solution.setup().run):
            solution.setup().run()
        else:
            get_active_logger().warn(
                'No "run" routine configured for solution "%s".' % solution.setup().name
            )
        if solution.setup().close and callable(solution.setup().close):
            solution.setup().close()
        get_active_logger().info("Finished %s" % solution.setup().name)

    @staticmethod
    def init_logging():
        """Initialize the logging for the script."""
        configure_logging(
            "script",
            loglevel=to_loglevel(get_loglevel_name()),
            stream_handler=sys.stdout,
            formatter_string=SolutionScript.get_script_logging_formatter_str(),
        )

    @staticmethod
    def api_access(
        solution: ISolution, package_path, installation_base_path, environment_path
    ):
        """Set the API access for the solution."""
        if package_path:
            solution.installation().set_package_path(package_path)
            sys.path.insert(0, str(solution.installation().package_path()))
        if installation_base_path:
            solution.installation().set_installation_path(installation_base_path)
            # add app_path to syspath
            sys.path.insert(0, str(solution.installation().app_path()))
        if environment_path:
            solution.installation().set_environment_path(environment_path)

    @staticmethod
    def append_arguments(solution: ISolution):
        """Append arguments to the solution."""
        parser = None
        if isinstance(solution.setup().args, str):
            SolutionScript._handle_args_string(solution.setup().args)
        else:
            parser = SolutionScript._handle_args_list(solution)
        return parser

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
    def _handle_args_list(solution: ISolution):
        parser = argparse.ArgumentParser(
            description="album run %s" % solution.setup().name
        )
        for arg in solution.setup().args:
            SolutionScript._add_parser_argument(solution, parser, arg)
        args = parser.parse_args()
        solution.set_args(args)
        return parser

    @staticmethod
    def _add_parser_argument(solution, parser, arg):
        keys = arg.keys()

        if "default" in keys and "action" in keys:
            get_active_logger().warning(
                "Default values cannot be automatically set when an action is provided! "
                "Ignoring default values..."
            )

        args = {}
        if "action" in keys:
            args["action"] = SolutionScript.make_action(solution, arg["name"])
        if "default" in keys:
            args["default"] = arg["default"]
        if "description" in keys:
            args["help"] = arg["description"]
        if "type" in keys:
            args["type"] = SolutionScript._parse_type(arg["type"])
        if "required" in keys:
            args["required"] = arg["required"]
        parser.add_argument("--%s" % arg["name"], **args)

    @staticmethod
    def _get_action_class_name(name):
        class_name = "%sAction" % name.capitalize()
        return class_name

    @staticmethod
    def strtobool(val):
        """Convert a string representation of truth to True or False."""
        val = val.lower()
        if val in ("y", "yes", "t", "true", "on", "1"):
            return True
        elif val in ("n", "no", "f", "false", "off", "0"):
            return False
        else:
            raise ValueError(f"invalid truth value {val!r}")

    @staticmethod
    def _parse_type(type_str):
        if type_str == "string":
            return str
        if type_str == "file":
            return Path
        if type_str == "directory":
            return Path
        if type_str == "integer":
            return int
        if type_str == "float":
            return float
        if type_str == "boolean":
            return SolutionScript.strtobool


def setup(**attrs):
    """Configure a solution for the use by the main album tool."""
    global _active_solution
    loglevel = os.getenv(DefaultValuesRunner.env_variable_logger_level.value, "INFO")
    configure_logging(
        "script",
        loglevel=to_loglevel(loglevel),
        stream_handler=sys.stdout,
        formatter_string=SolutionScript.get_script_logging_formatter_str(),
    )
    next_solution = Solution(attrs)
    push_active_solution(next_solution)
    goal = os.getenv(DefaultValuesRunner.env_variable_action.value, None)
    if goal:
        goal = Solution.Action[goal]
    package_path = os.getenv(
        DefaultValuesRunner.env_variable_package.value, os.path.abspath(__file__)
    )
    if package_path:
        package_path = Path(package_path)
    installation_base_path = os.getenv(
        DefaultValuesRunner.env_variable_installation.value, None
    )
    if installation_base_path:
        installation_base_path = Path(installation_base_path)
    environment_path = os.getenv(
        DefaultValuesRunner.env_variable_environment.value, None
    )
    if environment_path:
        environment_path = Path(environment_path)
    if goal:
        next_solution.installation().set_package_path(package_path)
        SolutionScript.trigger_solution_goal(
            next_solution, goal, package_path, installation_base_path, environment_path
        )


def push_active_solution(solution_object: ISolution):
    """Pop a solution to the _active_solution stack."""
    global _active_solution
    _active_solution.insert(0, solution_object)


def get_active_solution() -> Optional[ISolution]:
    """Return the currently active solution, which is defined globally."""
    global _active_solution
    if len(_active_solution) > 0:
        return _active_solution[0]
    return None


def pop_active_solution():
    """Pop the currently active solution from the _active_solution stack."""
    global _active_solution

    if len(_active_solution) > 0:
        return _active_solution.pop(0)
    else:
        return None


def in_target_environment() -> bool:
    """Give the boolean information whether current python is the python from the album target environment.

    Returns:
        True when current active python is the album target environment else False.

    """
    active_solution = get_active_solution()

    return (
        True
        if sys.executable.startswith(
            str(active_solution.installation().environment_path())
        )
        else False
    )


def get_environment_name() -> str:
    """Return the name of the environment the solution runs in."""
    from album.runner.api import get_environment_path

    return str(get_environment_path())


def get_environment_path():
    """Return the path of the environment the solution runs in."""
    active_solution = get_active_solution()
    res = active_solution.installation().environment_path()
    return Path(res) if res else res


def get_data_path() -> Path:
    """Return the data path provided for the solution."""
    active_solution = get_active_solution()
    res = active_solution.installation().data_path()
    return Path(res) if res else res


def get_package_path() -> Path:
    """Return the package path provided for the solution."""
    active_solution = get_active_solution()
    res = active_solution.installation().package_path()
    return Path(res) if res else res


def get_app_path() -> Path:
    """Return the app path provided for the solution."""
    active_solution = get_active_solution()
    res = active_solution.installation().app_path()
    return Path(res) if res else res


def get_cache_path() -> Path:
    """Return the cache path provided for the solution."""
    active_solution = get_active_solution()
    res = active_solution.installation().user_cache_path()
    return Path(res) if res else res


# necessary overwrite of the API of the old runner, DO NOT DELETE
_active_solution = []
import album.runner.api  # noqa: E402

album.runner.api.setup = setup
album.runner.api.get_active_solution = get_active_solution
album.runner.api.in_target_environment = in_target_environment
album.runner.api.get_environment_name = get_environment_name
album.runner.api.get_environment_path = get_environment_path
album.runner.api.get_data_path = get_data_path
album.runner.api.get_package_path = get_package_path
album.runner.api.get_app_path = get_app_path
album.runner.api.get_cache_path = get_cache_path

album.runner.album_logging.get_active_logger = get_active_logger
