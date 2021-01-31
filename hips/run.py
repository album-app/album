import os
import subprocess
import tempfile
import sys
from hips import Hips, get_active_hips, get_environment_name, hips_debug


def run_in_environment(environment_name, script):
    # environment_path = '/home/kharrin/anaconda3/envs/hips_full'
    environment_path = os.path.join(os.path.expanduser('~/'), 'anaconda3',
                                    'envs', environment_name)

    if hips_debug():
        print('run_in_environment: %s' % environment_path)

    # Using named environment doesn't work
    # condacli.run_command(condacli.Commands.RUN, '-n', environment_name,
    #                      'python', '-c', script)

    # Use an environment path and a temporary file to store the script
    if hips_debug():
        fp = open('/tmp/hips_test.py', 'w')
    else:
        fp = tempfile.NamedTemporaryFile(mode='w+')

    fp.write(script)
    fp.flush()
    os.fsync(fp)

    script_name = fp.name
    if hips_debug():
        print('script_name: %s' % script_name)
    #script_name = '/tmp/hips_test.py'
    #print('script: ' + script)

    # hips needs to be installed in the target environment
    # condacli.run_command(condacli.Commands.RUN, '--no-capture-output',
    #                     '--prefix', environment_path, 'python', script_name)

    # condacli.run_command(condacli.Commands.RUN, '--no-capture-output',
    #                      '--prefix', environment_path, 'python',
    #                      '/tmp/script_test.py')

    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix', environment_path,
        'python', script_name
    ]

    if hips_debug():
        print('subprocess.run: %s' % (' '.join(subprocess_args)))

    subprocess.run(subprocess_args)

    fp.close()


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
