import json
import os
import sys
import tempfile
from argparse import ArgumentError

from hips_utils import hips_logging

module_logger = hips_logging.get_active_logger


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
              "from hips import get_active_hips\n"
              "from hips_utils.hips_logging import configure_logging, LogLevel, get_active_logger\n"
              "module_logger = get_active_logger\n")
    # create logging
    script += "configure_logging(%s, \"%s\", sys.stdout," % (
        hips_logging.to_loglevel(hips_logging.get_loglevel_name()), hips_object['name']
    ) + "\"" + r"%(levelname)s - %(message)s" + "\")\n"
    # This could have an issue with nested quotes
    argv_string = ", ".join(argv)
    module_logger().debug("Add sys.argv arguments to runtime script: %s" % argv_string)
    script += "sys.argv = json.loads('%s')\n" % json.dumps(argv)
    script += hips_object['script']
    script += "\nhips.get_active_hips().init()\n"
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


def create_hips_with_parent_script(parent_hips, parent_args, child_hips_list, init_script):
    """Create script for running a parent HIPS, then running HIPS depending on it, and then closing the parent HIPS."""
    script_parent = create_script(parent_hips,
                                  init_script + "\nhips.get_active_hips().run()\n",
                                  parent_args)
    child_scripts = __create_scripts(child_hips_list)
    script_parent_close = ""
    if hasattr(parent_hips, "close"):
        script_parent_close += "\nhips.get_active_hips().close()\n"
    script_parent_close += "\nhips.pop_active_hips()\n"
    script_list = [script_parent]
    script_list.extend(child_scripts)
    script_list.append(script_parent_close)
    script = __append_scripts(*script_list)
    return script


def __create_scripts(child_hips_list):
    """Create scripts for a list of HIPs, each entry in `child_hips_list` consists of the loaded HIPS and it's
    arguments """
    child_scripts = []
    for child_hips in child_hips_list:
        active_hips = child_hips[0]
        child_args = child_hips[1]
        script = "\nhips.notify_active_hips_started(subprocess=True)\n"
        script += "\nhips.get_active_hips().run()\n"
        if hasattr(active_hips, "close"):
            script += "\nhips.get_active_hips().close()\n"
        script += "\nhips.notify_active_hips_finished(subprocess=True)\n"
        script += "\nhips.pop_active_hips()\n"
        child_scripts.append(create_script(active_hips, script, child_args))
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
