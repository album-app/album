import os
import subprocess
import tempfile
import sys
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
    script = ''

    # Evaluate the path
    # If the path is a file
    script += hips_script

    # If the path is a directory
    # If the path is a URL
    # If the path is the base of a git repo

    # Add the execution code
    script += """
hips.get_active_hips().init()
# now parse the HIPS, then run
hips.get_active_hips().main()"""

    run_in_environment(environment_name, script)
