import json
import os
import tempfile
from argparse import ArgumentError

from hips.core.model import logging

module_logger = logging.get_active_logger


def create_script(hips_object, custom_code, argv):
    """Creates the script which will later run custom_code in the environment of the hips_object.

    Args:
        hips_object:
            The hips object to create a solution for.
        custom_code:
            The code which will be executed by the returned script in the environment associated with the hips object
        argv:
            Arguments which should be appended to the script call

    Returns:
        The script as opened file.

    Raises:
        ArgumentError: When the arguments in the hips are not supported
    """
    # Create script to run within target environment
    script = ("import sys\n"
              "import json\n"
              "import argparse\n"
              "from hips.core import *\n"
              "from hips.core.model.logging import configure_logging, LogLevel, get_active_logger\n"
              "module_logger = get_active_logger\n")
    # create logging
    script += "configure_logging(%s, \"%s\", sys.stdout, " % (
        logging.to_loglevel(logging.get_loglevel_name()), hips_object['name']
    ) + "\"" + r"%(name)s - %(levelname)s - %(message)s" + "\")\n"
    script += "print = module_logger().info\n"
    # This could have an issue with nested quotes
    argv_string = ", ".join(argv)
    module_logger().debug("Add sys.argv arguments to runtime script: %s..." % argv_string)
    script += "sys.argv = json.loads('%s')\n" % json.dumps(argv)
    script += hips_object['script']
    script += "\nget_active_hips().init()\n"
    args = hips_object['args']
    script = __append_arguments(args, hips_object, script)
    script += custom_code
    return script


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


def create_hips_with_parent_script(parent_hips, parent_args, child_hips_list, child_args, init_script):
    """Create script for running a parent HIPS, then running HIPS depending on it, and then closing the parent HIPS."""
    script_parent = create_script(parent_hips,
                                  init_script + "\nget_active_hips().run()\n",
                                  parent_args)
    child_scripts = __create_scripts(child_hips_list, child_args)
    script_parent_close = ""
    if hasattr(parent_hips, "close"):
        script_parent_close += "\nget_active_hips().close()\n"
    script_parent_close += "\npop_active_hips()\n"
    script_list = [script_parent]
    script_list.extend(child_scripts)
    script_list.append(script_parent_close)
    script = __append_scripts(*script_list)
    return script


def __create_scripts(child_hips_list, child_args):
    """Create scripts for a list of HIPs, each entry in `child_hips_list` consists of the loaded HIPS and it's
    arguments """
    child_scripts = []
    for idx, active_hips in enumerate(child_hips_list):
        child_arg = child_args[idx]
        script = "\nmodule_logger().info(\"Started %s\")\n" % active_hips["name"]
        script += "\nget_active_hips().run()\n"
        if hasattr(active_hips, "close"):
            script += "\nget_active_hips().close()\n"
        script += "\nmodule_logger().info(\"Finished %s\")\n" % active_hips["name"]
        script += "\npop_active_hips()\n"
        child_scripts.append(create_script(active_hips, script, child_arg))
    return child_scripts


def __append_scripts(*scripts):
    """Create script running multiple scripts in a row"""
    res = ""
    for script in scripts:
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
        fp.write(script)
        fp.flush()
        os.fsync(fp)
        script_name = fp.name
        res += f"\nexec(open('{script_name}').read())\n"
        fp.close()
    return res
