import os
import sys
import subprocess
import tempfile
import yaml
import validators
import urllib.request
import logging
from pathlib import Path
from xdg import xdg_cache_home

DEBUG = False
module_logger = logging.getLogger('hips')


def hips_debug():
    return DEBUG


class Hips:
    """Encapsulates a HIPS."""
    setup_keywords = ('name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'main', 'install', 'author', 'author_email',
                      'long_description', 'git_repo', 'dependencies',
                      'timestamp', 'format_version', 'authors', 'cite', 'tags',
                      'documentation', 'covers', 'sample_inputs',
                      'sample_outputs', 'doi')

    private_setup_keywords = ('_environment_name', '_environment_path',
                              '_repository_path')

    def __init__(self, attrs=None):
        """sets object attributes in setup_keywords

        Args:
            attrs:
                Dictionary containing the attributes.
        """
        for attr in self.setup_keywords:
            if attr in attrs:
                setattr(self, attr, attrs[attr])

        # Attributes only available in the hips environment.
        for private_attr in self.private_setup_keywords:
            setattr(self, private_attr, "")

    def __str__(self):
        s = ''
        for attr in self.setup_keywords:
            if attr in dir(self):
                s += (attr + '\t' + str(getattr(self, attr))) + '\n'
        return s

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, key, value):
        if key in self.private_setup_keywords:
            setattr(self, key, value)

    def get_arg(self, k):
        """Get a specific named argument for this hips if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]


"""
Global variable for tracking the currently active HIPS. Do not use this 
directly instead use get_active_hips()
"""
global _active_hips
_active_hips = []


def setup(**attrs):
    """This configures a HIPS to for use by the main HIPS tool."""
    global _active_hips
    next_hips = Hips(attrs)
    _active_hips.insert(0, next_hips)


def get_active_hips():
    """Return the currently active HIPS, which is defined globally."""
    global _active_hips

    return _active_hips[0]


def pop_active_hips():
    """Pop the currently active hips from the _active_hips stack."""
    global _active_hips

    if len(_active_hips) > 0:
        return _active_hips.pop(0)
    else:
        return None


def parse_environment_name_from_yaml(yaml_env_path):
    """Reads out the "name" keywords from the environment yaml file

    Args:
        yaml_env_path: The path to the environment file

    Returns:
        The name of the environment.

    Raises:
        RuntimeError: When no valid environment file or name in hips dependency specified.
    """
    module_logger.debug('Parsing environment name form yaml: %s...' %
                        yaml_env_path)
    with open(yaml_env_path) as f:
        env = yaml.load(f, Loader=yaml.FullLoader)
    return env['name']


def set_environment_name(active_hips):
    """Get the environment name for a HIPS."""
    environment_name = ""
    if 'dependencies' in dir(active_hips):
        if 'environment_name' in active_hips['dependencies']:
            environment_name = active_hips['dependencies']['environment_name']
            module_logger.debug('Environment name explicit given as: %s...' %
                                environment_name)
        elif 'environment_file' in active_hips['dependencies']:
            env_file = active_hips['dependencies']['environment_file']
            module_logger.debug('Environment name implicit given in: %s...' %
                                env_file)

            # case valid path
            if Path.exists(Path(env_file)):
                yaml_path = env_file

            # case url
            elif validators.url(env_file):
                yaml_path = download_environment_yaml(active_hips)
                env_file = str(yaml_path)

            # don't know what to do
            else:
                message = 'No valid environment name or file specified! Don\'t know where to run solution'
                module_logger.error(message)
                raise RuntimeError(message)

            environment_name = parse_environment_name_from_yaml(yaml_path)
            module_logger.debug('Extracted following name from file: %s...' %
                                environment_name)

    else:
        environment_name = 'hips_full'
        module_logger.debug(
            'Environment name not given. Assume solution can be run in: %s...'
            % environment_name)

    active_hips["_environment_name"] = environment_name

    return environment_name


def download_environment_yaml(active_hips):
    """Downloads an environment_file.

     URL is specified in hips['dependencies']['environment_file']
    """
    environment_file = xdg_cache_home().joinpath('environment_file.yml')
    environment_url = active_hips['dependencies']['environment_file']
    module_logger.debug('Downloading environment file from %s into %s...' %
                        (environment_file, environment_url))

    urllib.request.urlretrieve(environment_url, environment_file)
    # ToDo: proper checking
    return environment_file


def run_in_environment(active_hips, script):
    """Runs the solution in the target environment

    Args:
        active_hips:
            The hips to run.
        script:
            The script calling the solution
    """
    module_logger.debug('run_in_environment: %s...' %
                        active_hips["_environment_path"])

    # Use an environment path and a temporary file to store the script
    if hips_debug():
        fp = open(str(xdg_cache_home().joinpath('hips_test.py')), 'w')
        module_logger.debug("Executable file in: %s..." %
                            str(xdg_cache_home().joinpath('hips_test.py')))
    else:
        fp = tempfile.NamedTemporaryFile(mode='w+')
        module_logger.debug('Executable file in: %s...' % fp.name)

    fp.write(script)
    fp.flush()
    os.fsync(fp)

    script_name = fp.name

    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix',
        active_hips["_environment_path"], 'python', script_name
    ]

    module_logger.debug('Running soltuion with subprocess command: %s...' %
                        " ".join(subprocess_args))

    subprocess.run(subprocess_args)

    fp.close()
