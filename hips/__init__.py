import conda.cli.python_api as condacli
import subprocess
import tempfile
import os

DEBUG = False


class Hips:
    """
    Encapsulates a HIPS
    """
    setup_keywords = ('name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'main', 'author', 'author_email',
                      'long_description', 'git_repo')

    def __init__(self, attrs=None):
        for attr in self.setup_keywords:
            if attr in attrs:
                setattr(self, attr, attrs[attr])

    def __str__(self):
        s = ''
        for attr in self.setup_keywords:
            if attr in dir(self):
                s += (attr + '\t' + str(getattr(self, attr))) + '\n'
        return s


global _active_hips


def setup(**attrs):
    """
    This configures a HIPS to for use by the main HIPS tool
    """
    global _active_hips
    _active_hips = Hips(attrs)


def get_active_hips():
    global _active_hips

    return _active_hips


def get_environment_name(hips):
    return 'hips_full'


def env_create(filename):
    # need to replicate behavior of this function:
    # https://github.com/conda/conda/blob/e37cf84a57f935c578cdcea6ea034c80d7677ccc/conda_env/cli/main_create.py#L76
    pass


def run_in_environment(environment_name, script):
    # environment_path = '/home/kharrin/anaconda3/envs/hips_full'
    environment_path = os.path.join(os.path.expanduser('~/'), 'anaconda3',
                                    'envs', environment_name)

    if DEBUG:
        print('run_in_environment: %s' % environment_path)

    # Using named environment doesn't work
    # condacli.run_command(condacli.Commands.RUN, '-n', environment_name,
    #                      'python', '-c', script)

    # Use an environment path and a temporary file to store the script
    if DEBUG:
        fp = open('/tmp/hips_test.py', 'w')
    else:
        fp = tempfile.NamedTemporaryFile(mode='w+')

    fp.write(script)
    fp.flush()

    script_name = fp.name
    if DEBUG:
        print('script_name: %s' % script_name)
    #script_name = '/tmp/hips_test.py'
    #print('script: ' + script)

    # hips needs to be installed in the target environment
    #condacli.run_command(condacli.Commands.RUN, '--no-capture-output',
    #                     '--prefix', environment_path, 'python', script_name)

    # condacli.run_command(condacli.Commands.RUN, '--no-capture-output',
    #                      '--prefix', environment_path, 'python',
    #                      '/tmp/script_test.py')

    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix', environment_path,
        'python', script_name
    ]

    if DEBUG:
        print('subprocess.run: %s' % (' '.join(subprocess_args)))

    subprocess.run(subprocess_args)

    fp.close()


def run(args):
    # Load HIPS
    hips_script = open(args.path).read()
    exec(hips_script)
    hips = get_active_hips()

    if DEBUG:
        print('hips loaded locally: ' + str(hips))

    # Get environment name
    environment_name = get_environment_name(hips)

    # If environment doesn't exist, then create it
    # Create an environment from a list of depndencies
    # condacli.run_command(condacli.Commands.CREATE, '-n', 'clitest', 'pyyaml', 'pytorch')

    # Create an environment from a yml
    # condacli.run_command(condacli.Commands.CREATE, '--file', 'hips_full.yml')

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
