import json
import sys
from argparse import ArgumentError

from album_runner import logging

module_logger = logging.get_active_logger
enc = sys.getfilesystemencoding()


def create_solution_script(solution_object, custom_code, argv):
    """Creates the script which will later run custom_code in the environment of the solution_object.

    Args:
        solution_object:
            The album object to create a solution for.
        custom_code:
            The code which will be executed by the returned script in the environment associated with the album object
        argv:
            Arguments which should be appended to the script call

    Returns:
        The script as opened file.

    Raises:
        ArgumentError: When the arguments in the album are not supported
    """
    process_name = solution_object['name']
    script = _generate_solution_block(solution_object)
    return create_script(process_name, script + custom_code, argv)


def create_script(process_name, custom_code, argv):
    """Creates the script which will run custom_code.

    Args:
        process_name:
            The name of the process.
        custom_code:
            The code which will be executed by the returned script in the environment associated with the album object
        argv:
            Arguments which should be appended to the script call

    Returns:
        The script as opened file.

    Raises:
        ArgumentError: When the arguments in the album are not supported
    """
    # Create script to run within target environment
    script = (
        "import sys\n"
        "import json\n"
        "import argparse\n"
        "from album_runner import *\n"
        "from album_runner.logging import configure_logging, LogLevel, get_active_logger\n"
        "module_logger = get_active_logger\n"
    )
    # create logging
    parent_name = logging.get_active_logger().name
    script += "configure_logging(\"%s\", loglevel=%s, stream_handler=sys.stdout, " % (
        process_name, logging.to_loglevel(logging.get_loglevel_name())
    ) + "formatter_string=\"" + r"%(name)s - %(levelname)s - %(message)s" + "\", parent_name=\"%s\")\n" % parent_name
    script += "print = module_logger().info\n"
    # This could have an issue with nested quotes
    argv_string = ", ".join(argv)
    module_logger().debug("Add sys.argv arguments to runtime script: %s..." % argv_string)
    script += "sys.argv = json.loads(r'%s')\n" % json.dumps(argv)
    script += custom_code
    return script


def _generate_solution_block(solution_object):
    # add the album script
    script = solution_object['script']
    # init routine
    script += "\nget_active_solution().init()\n"
    # API access
    script += __api_access(solution_object)
    args = solution_object['args']
    script += __append_arguments(args, solution_object)
    return script


def __api_access(active_solution):
    script = "album_runner_init("
    script += "environment_cache_path=" + "{}".format(str(active_solution.environment.cache_path).encode(enc)) + ", "
    script += "environment_path=" + "{}".format(str(active_solution.environment.path).encode(enc)) + ", "
    script += "environment_name=" + "{}".format(str(active_solution.environment.name).encode(enc)) + ", "
    script += "download_cache_path=" + "{}".format(str(active_solution.cache_path_download).encode(enc)) + ""
    script += ")\n"
    return script


def __append_arguments(args, solution_object):
    script = ""
    module_logger().debug(
        'Read out arguments in album solution and add to runtime script...')
    # special argument parsing cases
    if isinstance(args, str):
        __handle_args_string(args)
    else:
        script += __handle_args_list(args, solution_object)
    return script


def __handle_args_string(args):
    # pass through to module
    if args == 'pass-through':
        __handle_pass_through()
    else:
        message = 'Argument keyword \'%s\' not supported!' % args
        module_logger().error(message)
        raise ArgumentError(message)


def __handle_pass_through():
    module_logger().info(
        'Argument parsing not specified in album solution. Passing arguments through...'
    )


def __handle_args_list(args, solution_object):
    module_logger().debug('Add argument parsing for album solution to runtime script...')
    # Add the argument handling
    script = "\nparser = argparse.ArgumentParser(description='Album Run %s')\n" % solution_object['name']
    for arg in args:
        if 'action' in arg.keys():
            script += __create_action_class_string(arg)
        script += __create_parser_argument_string(arg)
    script += "\nget_active_solution().args = parser.parse_args()\n"
    return script


def __create_parser_argument_string(arg):
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
        class_name = __get_action_class_name(arg['name'])
        parse_arg += "action=%s, " % class_name  # CAUTION: no ''! action must be callable!
    parse_arg += ")\n"

    return parse_arg


def __create_action_class_string(arg):
    class_name = __get_action_class_name(arg['name'])
    return """
class {class_name}(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super({class_name}, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, get_active_solution().get_arg(self.dest)['action'](values))
        
""".format(class_name=class_name)


def __get_action_class_name(name):
    class_name = '%sAction' % name.capitalize()
    return class_name
