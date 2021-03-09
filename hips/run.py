import json
import logging
import sys
from argparse import ArgumentError

import hips
from utils.environment import set_environment_path, set_environment_name, run_in_environment

module_logger = logging.getLogger('hips')

# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)
# ToDo: solutions should not run in hips.yml for comp. reasons. Maybe check that?


def create_run_script(hips_object):
    """Creates the script which will later run a solution.

    Args:
        hips_object:
            The hips object to create a solution for.

    Returns:
        The script as opened file.

    Raises:
        ArgumentError: When the arguments in the hips are not supported
    """
    # Create script to run within target environment
    script = """import sys
import json
import argparse
from hips import get_active_hips
"""

    # This could have an issue with nested quotes
    module_logger.debug("Add sys.argv arguments to runtime script: %s" %
                        ", ".join(sys.argv))
    script += "sys.argv = json.loads('%s')\n" % json.dumps(sys.argv)

    # Evaluate the path
    # If the path is a file
    script += hips_object['script']

    # Add the init code
    script += """
hips.get_active_hips().init()
    """

    args = hips_object['args']

    module_logger.debug(
        'Read out arguments in hips solution and add to runtime script...')
    # special argument parsing cases
    if isinstance(args, str):
        # pass through to module
        if args == 'pass-through':
            module_logger.info(
                'Argument parsing not specified in hips solution. Passing arguments through...'
            )
            pass
        # read arguments from file
        elif args == 'read-from-file':
            pass  # ToDo: discuss if we want this!
        else:
            message = 'Argument keyword \'%s\' not supported!' % args
            module_logger.error(message)
            raise ArgumentError(message)

    else:
        module_logger.debug(
            'Add argument parsing for hips solution to runtime script...')
        # Add the argument handling
        script += """
parser = argparse.ArgumentParser(description='HIPS Run %s')
    """ % hips_object['name']

        for arg in args:
            class_name = '%sAction' % arg['name'].capitalize()

            # Create an action
            script += """
class {class_name}(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super({class_name}, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        get_active_hips().get_arg(self.dest)['action'](values)
    """.format(class_name=class_name)

            # Add an argument
            script += """
parser.add_argument('--{name}',
                    default='{default}',
                    help='{description}',
                    action={class_name})
""".format(name=arg['name'],
            default=arg['default'],
            description=arg['description'],
            class_name=class_name)

        script += """
parser.parse_args()
    """

    # Add the run code
    script += """
hips.get_active_hips().run()
"""

    return script


def run(args):
    """Function corresponding to the `run` subcommand of `hips`."""

    hips.load_and_push_hips(args.path)

    active_hips = hips.get_active_hips()
    set_environment_name(active_hips)
    set_environment_path(active_hips)
    script = create_run_script(active_hips)
    run_in_environment(active_hips, script)

    hips.pop_active_hips()
