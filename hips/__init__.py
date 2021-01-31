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
                      'long_description', 'git_repo', 'dependencies')

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
