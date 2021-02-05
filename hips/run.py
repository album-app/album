import os
import subprocess
import tempfile
import sys
import json
from argparse import ArgumentError

from hips import Hips, get_active_hips, get_environment_name, hips_debug, run_in_environment


def create_environment(hips):
    environment_name = get_environment_name(hips)
    # Create an environment from a list of depndencies
    # condacli.run_command(condacli.Commands.CREATE, '-n', 'clitest', 'pyyaml', 'pytorch')

    # Create an environment from a yml
    if environment_name == 'hips_full':
        condacli.run_command(condacli.Commands.CREATE, '--file',
                             'hips_full.yml')


def environment_exists(environment_name):
    output = subprocess.check_output(['conda', 'info', '--envs'])
    lines = output.split(b"\n")
    env_lines = lines[2:-1]
    [print(l) for l in env_lines]


def run(args):
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()

    if hips_debug():
        print('hips loaded locally: ' + str(hips))

    # Get environment name
    environment_name = get_environment_name(hips)

    # If environment doesn't exist, then create it
    # if not environment_exists(environment_name):
    #     create_environment(hips)

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

    args = get_active_hips()['args']

    # special argument parsing cases
    if isinstance(args, str):
        # pass through to module
        if args == 'pass-through':
            pass
        # read arguments from file
        elif args == 'read-from-file':
            pass  # ToDo: discuss if we want this!
        else:
            raise ArgumentError('Argument keyword \'%s\' not supported!' % args)
    else:
        # Add the argument handling
        script += """
parser = argparse.ArgumentParser(description='HIPS Run %s')
""" % hips['name']

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

    run_in_environment(environment_name, script)
