import abc
import json
import sys
from argparse import ArgumentError

from album.core.model.solution import Solution
from album.runner import album_logging

# CAUTION: DO NOT IMPORT DEPENDENCIES THAT REQUIRE A LIBRARY INSTALLATION

module_logger = album_logging.get_active_logger
enc = sys.getfilesystemencoding()


# FIXME: make this an own controller that can handle cript creation. INLETS should also move here?!?
# FIXME: SHOULD this live in the runner? as script creator and runner belong together?
# FIXME: if script creator and runner belong together then also the solution class, right?
# FIXME: if you give the creator a solution object it cannot deal with -> error
# FIXME: so the solution object should be versioned?

class ScriptCreator(abc.ABC):
    """Abstract class for all ScriptCreator classes. Holds methods shared across all ScriptCreator classes."""

    def __init__(self, execution_callback=None):
        self.execution_block = None
        self.common_inset = None
        if execution_callback is not None and callable(execution_callback):
            self.execution_callback = execution_callback
        else:
            self.reset_callback()

    def reset_callback(self):
        self.execution_callback = lambda: ""

    @abc.abstractmethod
    def set_execution_block(self, solution_object):
        """The custom code for all scripts created by this class"""
        pass

    @abc.abstractmethod
    def set_common_inset(self, solution_object):
        pass

    def create_script(self, solution_object, argv) -> str:
        """Creates the script with the execution_block of the concrete instance of the class"""
        self.set_common_inset(solution_object)
        self.set_execution_block(solution_object)

        script = Script(solution_object, self.execution_block, argv)

        return script.create_solution_script()


class ScriptCreatorInstall(ScriptCreator):
    def __init__(self):
        super().__init__()

    def set_execution_block(self, _):
        self.execution_block = "\nget_active_solution().install()\n"

    def set_common_inset(self, _):
        self.common_inset = ""


class ScriptCreatorUnInstall(ScriptCreator):
    def __init__(self):
        super().__init__()

    def set_execution_block(self, _):
        self.execution_block = "\nget_active_solution().uninstall()\n"

    def set_common_inset(self, _):
        self.common_inset = ""


class ScriptCreatorRun(ScriptCreator):
    def __init__(self, pop_solution: bool = False, execution_callback=None):
        super().__init__(execution_callback)
        self.pop_solution = pop_solution

    def set_common_inset(self, _):
        self.common_inset = ""

    def set_execution_block(self, solution_object: Solution):
        execution_block = self.common_inset
        execution_block += "\nmodule_logger().info(\"Starting %s\")" % solution_object["name"]
        execution_block += "\nmodule_logger().info(\"\")\n"
        if solution_object['run'] and callable(solution_object['run']):
            execution_block += "\nget_active_solution().run()\n"
        else:
            raise ValueError("No \"run\" routine specified for solution \"%s\"! Aborting..." % solution_object["name"])

        execution_block += self.execution_callback()

        if solution_object['close'] and callable(solution_object['close']):
            execution_block += "\nget_active_solution().close()\n"

        execution_block += "\nmodule_logger().info(\"\")"
        execution_block += "\nmodule_logger().info(\"Finished %s\")\n" % solution_object["name"]

        if self.pop_solution:
            execution_block += "\npop_active_solution()\n"

        self.execution_block = execution_block


class ScriptTestCreator(ScriptCreatorRun):
    def __init__(self):
        super().__init__()

    def set_common_inset(self, solution_object):
        common_inset = "\nd = get_active_solution().pre_test()\n"
        common_inset += "\nsys.argv = sys.argv + [\"=\".join([c, d[c]]) for c in d]\n"

        # parse args again after pre_test() routine if necessary.
        if not solution_object["args"] == "pass-through":
            common_inset += "\nget_active_solution().args = parser.parse_args()\n"

        self.common_inset = common_inset

    def set_execution_block(self, solution_object):
        super().set_execution_block(solution_object)
        self.execution_block += "\nget_active_solution().test()\n"


class Script:
    def __init__(self, solution_object, execution_block, argv):
        self.solution_object = solution_object
        self.execution_block = execution_block
        self.argv = argv

    def create_solution_script(self):
        script = self._create_header()
        script += self._create_body()
        script += self.execution_block

        return script

    def _create_header(self):
        header = (
            "import sys\n"
            "import json\n"
            "import argparse\n"
            "from album.runner import *\n"
            "from album.runner.album_logging import configure_logging, LogLevel, get_active_logger\n"
            "module_logger = get_active_logger\n"
        )
        # create logging
        parent_name = album_logging.get_active_logger().name
        header += "configure_logging(\"%s\", loglevel=%s, stream_handler=sys.stdout, " % (
            self.solution_object['name'], album_logging.to_loglevel(album_logging.get_loglevel_name())
        ) + "formatter_string=\"" + r"%(name)s - %(levelname)s - %(message)s" + "\", parent_name=\"%s\")\n" % parent_name
        header += "print = module_logger().info\n"
        # This could have an issue with nested quotes
        module_logger().debug("Add sys.argv arguments to runtime script: %s..." % ", ".join(self.argv))
        header += "sys.argv = json.loads(r'%s')\n" % json.dumps(self.argv)

        return header

    def _create_body(self):
        # add the album script
        script = self.solution_object['script']
        # init routine
        # script += "\nget_active_solution().init()\n" THIS FEATURE IS TEMPORARY DISABLED
        # API access
        script += self._api_access()

        script += self._append_arguments(self.solution_object['args'])
        return script

    def _api_access(self):
        # mapping from internal paths to API paths for the user
        script = "album_runner_init("
        script += "environment_path=" + "{}".format(str(self.solution_object.environment.path).encode(enc)) + ", "
        script += "environment_name=" + "{}".format(str(self.solution_object.environment.name).encode(enc)) + ", "
        script += "data_path=" + "{}".format(str(self.solution_object.data_path).encode(enc)) + ", "
        script += "package_path=" + "{}".format(str(self.solution_object.package_path).encode(enc)) + ", "
        script += "app_path=" + "{}".format(str(self.solution_object.app_path).encode(enc)) + ", "
        script += "cache_path=" + "{}".format(str(self.solution_object.cache_path).encode(enc))
        script += ")\n"
        return script

    def _append_arguments(self, args):
        script = ""
        module_logger().debug(
            'Read out arguments in album solution and add to runtime script...')
        # special argument parsing cases
        if isinstance(args, str):
            self._handle_args_string(args)
        else:
            script += self._handle_args_list(args)
        return script

    @staticmethod
    def _handle_args_string(args):
        # pass through to module
        if args == 'pass-through':
            module_logger().info(
                'Argument parsing not specified in album solution. Passing arguments through...'
            )
        else:
            message = 'Argument keyword \'%s\' not supported!' % args
            module_logger().error(message)
            raise ArgumentError(message)

    def _handle_args_list(self, args):
        module_logger().debug('Add argument parsing for album solution to runtime script...')
        # Add the argument handling
        script = "\nparser = argparse.ArgumentParser(description='Album Run %s')\n" % self.solution_object['name']
        for arg in args:
            if 'action' in arg.keys():
                script += self._create_action_class_string(arg)
            script += self._create_parser_argument_string(arg)
        script += "\nget_active_solution().args = parser.parse_args()\n"
        return script

    def _create_parser_argument_string(self, arg):
        keys = arg.keys()

        if 'default' in keys and 'action' in keys:
            module_logger().warning("Default values cannot be automatically set when an action is provided! "
                                    "Ignoring default values...")

        parse_arg = "parser.add_argument('--%s', " % arg['name']
        if 'default' in keys:
            parse_arg += "default='%s', " % arg['default']
        if 'description' in keys:
            parse_arg += "help='%s', " % arg['description']
        if 'required' in keys:
            parse_arg += "required=%s, " % arg['required']  # CAUTION: no ''! Boolean value
        if 'action' in keys:
            class_name = self._get_action_class_name(arg['name'])
            parse_arg += "action=%s, " % class_name  # CAUTION: no ''! action must be callable!
        parse_arg += ")\n"

        return parse_arg

    def _create_action_class_string(self, arg):
        class_name = self._get_action_class_name(arg['name'])
        return """
class {class_name}(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super({class_name}, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, get_active_solution().get_arg(self.dest)['action'](values))

""".format(class_name=class_name)

    @staticmethod
    def _get_action_class_name(name):
        class_name = '%sAction' % name.capitalize()
        return class_name
