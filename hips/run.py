import json
import subprocess
import sys
import logging
from argparse import ArgumentError

import hips


module_logger = logging.getLogger('hips')


# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)
# ToDo: solutions should not run in hips.yml for comp. reasons. Maybe check that?

# ToDo: maybe find a nice way than extracting stuff from some console output?
#  The current solution might be highly risky...
def _get_environment_dict():
    """Returns the conda environments available for the conda installation."""
    environment_dict = dict()

    # remove empty lines and preceded information
    def _split_and_clean(line_str):
        return None if line_str == '' or line_str.startswith('#') else line_str.replace('\r', '').split(' ')

    # list environments via conda info command - Note: conda.cli.python_api support missing
    module_logger.debug('List available conda environments...')
    output = subprocess.check_output(['conda', 'info', '--envs']).decode("utf-8")
    lines = output.split("\n")

    # extract name and path
    module_logger.debug('Parse conda info output...')
    for line in lines:
        parsed_line = _split_and_clean(line)
        if parsed_line:
            # name is first split in line, path last
            environment_dict[parsed_line[0]] = parsed_line[-1]

    return environment_dict


def set_environment_path(hips_object):
    """Sets the hips attribute and returns the full environment path.

    Args:
        hips_object:
            The hips object to create a solution for.

    Raises:
        RuntimeError: When the environment could not be found.
    """
    environment_dict = _get_environment_dict()
    if hips_object["_environment_name"] in environment_dict.keys():

        environment_path = environment_dict[hips_object["_environment_name"]]

        module_logger.debug('Set environment path to %s' % environment_path)
        hips_object["_environment_path"] = environment_path

        return environment_path
    else:
        message = 'Could not find environment!'
        module_logger.error(message)
        raise RuntimeError(message)


# ToDo: decide where to put create_environment method
def create_or_update_environment(hips_object):
    """Creates environment a solution runs in.

    Args:
        hips_object:
            The hips object to create a solution for.

    Returns:
        The complete environment path.
    """
    environment_name = hips.set_environment_name(hips_object)

    if environment_exists(environment_name):  # updates environment
        module_logger.debug('Update environment %s...' % environment_name)
        pass  # ToDo: implement
    elif 'environment_file' in hips_object['dependencies']:
        file = hips_object['dependencies']['environment_file']
        module_logger.debug('Found environment file %s in hips dependencies...' % file)
        subprocess_args = [
            'conda', 'env', 'create', '-f', file
        ]
        module_logger.debug('Create environment with subprocess:  %s...' % " ".join(subprocess_args))
        subprocess.run(subprocess_args)

    else:
        module_logger.debug('No environment specified in hips dependencies. Taking %s environment...' % 'hips_full')
        subprocess_args = ['conda', 'env', 'create', '-f', 'hips_full.yml']  # ToDo: get rid of hardcoded stuff
        module_logger.debug('Create environment with subprocess: %s...' % " ".join(subprocess_args))
        subprocess.run(subprocess_args)

    # set environment path
    environment_path = set_environment_path(hips_object)

    # update environment to fit hips needs
    install_hips_in_environment(hips_object)

    return environment_path


# ToDo: use explicit versioning of hips
def install_hips_in_environment(hips_object):
    """Installs the hips dependency in the environment

    Args:
        hips_object:
            The hips object to create a solution for.
    """
    environment_path = hips_object["_environment_path"]
    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix', environment_path,
        'pip', 'install', 'git+https://gitlab.com/ida-mdc/hips.git'
    ]
    module_logger.debug('Install hips in target environment with subprocess: %s...' % " ".join(subprocess_args))
    subprocess.run(subprocess_args)


# ToDo: decide where to put environment_exists method
def environment_exists(environment_name):
    """Checks whether an environmment already exists or not.

    Args:
        environment_name:
            The name of the environment in which a solution will run.

    Returns:
        True when environment exists else false.
    """
    environment_dict = _get_environment_dict()
    return True if environment_name in environment_dict.keys() else False


def create_run_script(hips_object, hips_script):
    """Creates the script which will later run a solution.

    Args:
        hips_object:
            The hips object to create a solution for.
        hips_script:
            The script file to write to.

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
    script += "sys.argv = json.loads('%s')\n" % json.dumps(sys.argv)

    # Evaluate the path
    # If the path is a file
    script += hips_script

    # Add the init code
    script += """
hips.get_active_hips().init()
    """

    args = hips_object['args']

    module_logger.debug('Read out arguments in hips solution and add to runtime script...')
    # special argument parsing cases
    if isinstance(args, str):
        # pass through to module
        if args == 'pass-through':
            module_logger.info('Argument parsing not specified in hips solution. Passing arguments through...')
            pass
        # read arguments from file
        elif args == 'read-from-file':
            pass  # ToDo: discuss if we want this!
        else:
            message = 'Argument keyword \'%s\' not supported!' % args
            module_logger.error(message)
            raise ArgumentError(message)

    else:
        module_logger.debug('Add argument parsing for hips solution to runtime script...')
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
hips.get_active_hips().main()"""

    return script


def run(args):
    """Function corresponding to the `run` subcommand of `hips`."""

    module_logger.debug('Load hips...')
    hips_script = open(args.path).read()
    exec(hips_script)

    active_hips = hips.get_active_hips()

    module_logger.debug('hips loaded locally: %s' % str(active_hips))

    # update or create environment
    create_or_update_environment(active_hips)

    # execute install routine
    if hasattr(active_hips, 'install') and callable(active_hips['install']):
        module_logger.debug('Calling install routine specified in solution...')
        active_hips.install()

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    script = create_run_script(active_hips, hips_script)

    hips.run_in_environment(active_hips, script)
