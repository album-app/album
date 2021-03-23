import json
import sys
from argparse import ArgumentError

from utils import hips_logging

module_logger = hips_logging.get_active_logger


def create_script(hips_object, custom_code):
    """Creates the script which will later run custom_code in the environment of the hips_object.

    Args:
        hips_object:
            The hips object to create a solution for.
        custom_code:
            The code which will be executed by the returned script in the environment associated with the hips object

    Returns:
        The script as opened file.

    Raises:
        ArgumentError: When the arguments in the hips are not supported
    """
    # Create script to run within target environment
    script = ("import sys\n"
              "import json\n"
              "import argparse\n"
              "from hips import get_active_hips\n")
    # This could have an issue with nested quotes
    argv_string = ", ".join(sys.argv)
    module_logger().debug("Add sys.argv arguments to runtime script: %s" % argv_string)
    script += "sys.argv = json.loads('%s')\n" % json.dumps(sys.argv)
    script += hips_object['script']
    script += "\nhips.get_active_hips().init()\n"
    args = hips_object['args']
    script = __append_arguments(args, hips_object, script)
    script += custom_code
    return script


def __append_hips_init_call():
    return "\nhips.get_active_hips().init()\n"


def __append_arguments(args, hips_object, script):
    module_logger().debug(
        'Read out arguments in hips solution and add to runtime script...')
    # special argument parsing cases
    if isinstance(args, str):
        __handle_args_string(args)
    else:
        script = __handle_args_list(args, hips_object, script)
    return script


def __handle_args_string(args):
    # pass through to module
    if args == 'pass-through':
        __handle_pass_through()
    # read arguments from file
    elif args == 'read-from-file':
        pass  # ToDo: discuss if we want this!
    else:
        message = 'Argument keyword \'%s\' not supported!' % args
        module_logger().error(message)
        raise ArgumentError(message)


def __handle_pass_through():
    module_logger().info(
        'Argument parsing not specified in hips solution. Passing arguments through...'
    )
    pass


def __handle_args_list(args, hips_object, script):
    module_logger().debug(
        'Add argument parsing for hips solution to runtime script...')
    # Add the argument handling
    script += "\nparser = argparse.ArgumentParser(description='HIPS Run %s')\n" % hips_object['name']
    for arg in args:
        script += __create_action_class_string(arg)
        script += __create_parser_argument_string(arg)
    script += "\nparser.parse_args()\n"
    return script


def __create_parser_argument_string(arg):
    class_name = __create_class_name(arg['name'])
    return """
parser.add_argument('--{name}',
                    default='{default}',
                    help='{description}',
                    action={class_name})
""".format(name=arg['name'],
           default=arg['default'],
           description=arg['description'],
           class_name=class_name)


def __create_action_class_string(arg):
    class_name = __create_class_name(arg['name'])
    return """
class {class_name}(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super({class_name}, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        get_active_hips().get_arg(self.dest)['action'](values)
    """.format(class_name=class_name)


def __create_class_name(name):
    class_name = '%sAction' % name.capitalize()
    return class_name
