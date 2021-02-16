import json
import subprocess
import sys
from argparse import ArgumentError

import hips


# ToDo: maybe find a nice way than extracting stuff from some console output?
#  The current solution might be highly risky...
def _get_environment_dict():
    """
    Returns the conda environments available for the conda installation
    """
    environment_dict = dict()

    # remove empty lines and preceded information
    def _split_and_clean(line_str):
        return None if line_str == '' or line_str.startswith('#') else line_str.replace('\r', '').split(' ')

    # list environments via conda info command - Note: conda.cli.python_api support missing
    output = subprocess.check_output(['conda', 'info', '--envs']).decode("utf-8")
    lines = output.split("\n")

    # extract name and path
    for line in lines:
        parsed_line = _split_and_clean(line)
        if parsed_line:
            # name is first split in line, path last
            environment_dict[parsed_line[0]] = parsed_line[-1]

    return environment_dict


def set_environment_path(hips_object):
    """
    Sets the hips attribute and returns the full environment path
    """
    environment_dict = _get_environment_dict()
    if hips_object["_environment_name"] in environment_dict.keys():
        # get path
        environment_path = environment_dict[hips_object["_environment_name"]]
        # set path
        hips_object["_environment_path"] = environment_path
        # return path
        return environment_path
    else:
        raise RuntimeError('Could not find environment!')


# ToDo: decide where to put create_environment method
def create_environment(hips_object):
    environment_name = hips.set_environment_name(hips_object)

    if environment_exists(environment_name):  # updates environment
        pass
    elif 'environment_file' in hips_object['dependencies']:
        file = hips_object['dependencies']['environment_file']
        subprocess_args = [
            'conda', 'env', 'create', '-f', file
        ]
        subprocess.run(subprocess_args)

    else:
        subprocess_args = ['conda', 'env', 'create', '-f', 'hips_full.yml']
        subprocess.run(subprocess_args)

    # set environment path
    environment_path = set_environment_path(hips_object)

    # update environment to fit hips needs
    install_hips_in_environment(hips_object)

    return environment_path


# ToDo: use explicit versioning of hips
def install_hips_in_environment(hips_object):
    environment_path = hips_object["_environment_path"]
    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix', environment_path,
        'pip', 'install', 'git+https://gitlab.com/ida-mdc/hips.git'
    ]
    subprocess.run(subprocess_args)


# ToDo: decide where to put environment_exists method
def environment_exists(environment_name):
    """
    Returns True when the given environment name exists for the conda installation else False
    """
    environment_dict = _get_environment_dict()
    return True if environment_name in environment_dict.keys() else False


# ToDo: proper logging system for hips?
# ToDo: environment purge method
# ToDo: reusable versioned environments?
# ToDo: test for windows
# ToDo: subprocess logging (https://www.endpoint.com/blog/2015/01/28/getting-realtime-output-using-python)

def create_run_script(hips_object, hips_script):

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

    # special argument parsing cases
    if isinstance(args, str):
        # pass through to module
        if args == 'pass-through':
            pass
        # read arguments from file
        elif args == 'read-from-file':
            pass  # ToDo: discuss if we want this!
        else:
            raise ArgumentError('Argument keyword \'%s\' not supported!' %
                                args)
    else:
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
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    active_hips = hips.get_active_hips()

    if hips.hips_debug():
        print('hips loaded locally: ' + str(active_hips))

    # update or create environment
    create_environment(active_hips)

    # execute install routine
    if hasattr(active_hips, 'install') and callable(active_hips['install']):
        active_hips.install()

    # ToDo: install helper - methods (pip install) (git-download) (java-dependcies)

    script = create_run_script(active_hips, hips_script)

    hips.run_in_environment(active_hips, script)
