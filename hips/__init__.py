# import conda.cli.python_api as condacli
import subprocess
import tempfile
import os
import yaml
import sys

DEBUG = False


def hips_debug():
    return DEBUG


class Hips:
    """
    Encapsulates a HIPS
    """
    setup_keywords = ('name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'main', 'author', 'author_email',
                      'long_description', 'git_repo', 'dependencies',
                      'timestamp', 'format_version', 'authors', 'cite',
                      'tags', 'documentation', 'covers', 'sample_inputs',
                      'sample_outputs')

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

    def __getitem__(self, k):
        return getattr(self, k)

    def get_arg(self, k):
        """
        Get a specific named argument for this hips if it exists
        """
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]


"""
Global variable for tracking the currently active HIPS. Do not use this 
directly instead use get_active_hips()
"""
global _active_hips


def setup(**attrs):
    """
    This configures a HIPS to for use by the main HIPS tool
    """
    global _active_hips
    _active_hips = Hips(attrs)


def get_active_hips():
    """
    Return the currently active HIPS, which is defined globally
    """
    global _active_hips

    return _active_hips


def get_environment_name(hips):
    """
    Get the environment name for a HIPS
    """
    if ('dependencies' in dir(hips)):
        if ('environment_name' in hips['dependencies']):
            return hips['dependencies']['environment_name']
        else:
            yaml_path = hips['dependencies']['environment_path']
            # Read from YAML
            env: dict
            with open(yaml_path) as f:
                env = yaml.load(f, Loader=yaml.FullLoader)
            return env['name']
    else:
        return 'hips_full'


def env_create(filename):
    # need to replicate behavior of this function:
    # https://github.com/conda/conda/blob/e37cf84a57f935c578cdcea6ea034c80d7677ccc/conda_env/cli/main_create.py#L76
    pass


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
