import json
import os
import subprocess
import tempfile
from io import StringIO
from pathlib import Path

import validators
import yaml
from xdg import xdg_cache_home

from hips.core import hips_debug
from hips.core.model.configuration import HipsConfiguration
from hips.core.utils import subcommand
from hips.core.model import logging
from hips.core.utils.operations.file_operations import create_path_recursively, copy
from hips.core.utils.operations.url_operations import download_resource

module_logger = logging.get_active_logger


def parse_environment_name_from_yaml(yaml_env_path):
    """Reads out the "name" keywords from the environment yaml file

    Args:
        yaml_env_path: The path to the environment file

    Returns:
        The name of the environment.

    Raises:
        RuntimeError: When no valid environment file or name in hips dependency specified.
    """
    module_logger().debug('Parsing environment name form yaml: %s...' % yaml_env_path)
    with open(yaml_env_path) as f:
        # todo: use safe_load to avoid code injection
        env = yaml.load(f, Loader=yaml.FullLoader)
    return env['name']


def set_environment_name(active_hips):
    """Get the environment name for a HIPS."""
    environment_name = ""
    if 'dependencies' in dir(active_hips):

        if 'environment_name' in active_hips['dependencies']:
            environment_name = active_hips['dependencies']['environment_name']
            module_logger().debug('Environment name explicit given as: %s...' % environment_name)

        elif 'environment_file' in active_hips['dependencies']:
            env_file = active_hips['dependencies']['environment_file']
            module_logger().debug('Environment name implicit given in: %s...' % env_file)

            yaml_path = get_environment_file(env_file, active_hips)

            environment_name = parse_environment_name_from_yaml(yaml_path)
            module_logger().debug('Extracted following name from file: %s...' %
                                  environment_name)

    else:
        environment_name = 'hips_full'
        module_logger().debug(
            'Environment name not given. Assume solution can be run in: %s...'
            % environment_name)

    active_hips["_environment_name"] = environment_name

    return environment_name


def set_environment_path(active_hips):
    """Sets the hips attribute and returns the full environment path.

    Args:
        active_hips:
            The hips object to create a solution for.

    Raises:
        RuntimeError: When the environment could not be found.
    """
    environment_dict = get_environment_dict()
    environment_name = active_hips["_environment_name"]
    if environment_name in environment_dict.keys():

        environment_path = environment_dict[environment_name]

        module_logger().debug('Set environment path to %s...' % environment_path)
        active_hips["_environment_path"] = environment_path

        return environment_path
    else:
        raise RuntimeError('Could not find environment!')


def get_environment_dict():
    """Returns the conda environments available for the conda installation."""
    environment_dict = dict()

    # list environments via conda info command - Note: conda.cli.python_api support missing
    module_logger().debug('List available conda environments...')
    output = subprocess.check_output(['conda', 'info', '--json']).decode("utf-8")
    conda_info = json.loads(output)

    for env in conda_info["envs"]:
        environment_dict[os.path.basename(env)] = env

    return environment_dict


# todo: write tests
def is_installed(environment_path, package_name, min_package_version=None):
    subprocess_args = [
        'conda', 'list', '--json', '--prefix', environment_path,
    ]
    output = subprocess.check_output(subprocess_args).decode("utf-8")
    conda_list = json.loads(output)

    for package in conda_list:
        if package["name"] == package_name:
            if min_package_version:
                if package["version"] == min_package_version:
                    module_logger().debug('Package %s:%s is installed...' % (package_name, min_package_version))
                    return True
                if package["version"] < min_package_version:
                    module_logger().debug('Package %s:%s is installed. Requirements not set! Reinstalling...'
                                          % (package_name, package["version"]))
                    return False
                if package["version"] > min_package_version:
                    module_logger().debug('Package %s:%s is installed. Version should be compatible...'
                                          % (package_name, package["version"]))
                    return True
            else:
                module_logger().debug('Package %s:%s is installed...' % (package_name, package["version"]))
                return True

    return False


def get_environment_file(env_file, active_hips):
    """Handles the environment file dependency. Returns path to the file. Either downloads file or parses from stream"""
    configuration = HipsConfiguration()
    yaml_path = configuration.get_cache_path_hips(active_hips).joinpath("%s%s" % (active_hips["name"], ".yml"))
    create_path_recursively(yaml_path.parent)

    if isinstance(env_file, str):
        # case valid url
        if validators.url(env_file):
            return download_resource(env_file, yaml_path)

        # case Path
        elif Path(env_file).is_file() and Path(env_file).stat().st_size > 0:
            copy(env_file, yaml_path)
            return yaml_path

    # case String stream
    elif isinstance(env_file, StringIO):
        with open(yaml_path, "w+") as f:
            env_file.seek(0)  # make sure we start from the beginning
            f.writelines(env_file.readlines())
        return yaml_path

    raise RuntimeError('No valid environment name or file specified! Don\'t know where to run solution!')


def run_in_environment(environment_path, script):
    """Runs the solution in the target environment

    Args:
        environment_path:
            The name of the environment path to run the script in.
        script:
            The script calling the solution
    """
    module_logger().debug('run_in_environment: %s...' % environment_path)

    # Use an environment path and a temporary file to store the script
    if hips_debug():
        fp = open(str(xdg_cache_home().joinpath('hips_test.py')), 'w')
        module_logger().debug("Executable file in: %s..." % str(xdg_cache_home().joinpath('hips_test.py')))
    else:
        fp = tempfile.NamedTemporaryFile(mode='w+')
        module_logger().debug('Executable file in: %s...' % fp.name)

    fp.write(script)
    fp.flush()
    os.fsync(fp)

    script_name = fp.name

    # conda run necessary to correctly initialize python
    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix',
        environment_path, 'python', script_name
    ]

    subcommand.run(subprocess_args)

    fp.close()


def create_or_update_environment(active_hips):
    """Creates environment a solution runs in.

    Args:
        active_hips:
            The hips object to create a solution for.

    Returns:
        The complete environment path.
    """
    environment_name = set_environment_name(active_hips)

    if environment_exists(environment_name):  # updates environment
        module_logger().debug('Update environment %s...' % environment_name)
        pass  # ToDo: implement
    elif 'environment_file' in active_hips['dependencies']:
        env_file = get_environment_file(active_hips['dependencies']['environment_file'], active_hips)

        module_logger().debug('Environment file %s in hips dependencies...' % env_file)

        subprocess_args = ['conda', 'env', 'create', '-q', '-f', str(env_file)]
        try:
            subcommand.run(subprocess_args)
        except RuntimeError as e:
            # cleanup after failed installation
            if environment_exists(environment_name):
                module_logger().debug('Cleanup failed installation...')
                subprocess_args = ['conda', 'env', 'remove', '-q', '-n', environment_name]
                subcommand.run(subprocess_args)
            raise RuntimeError("Command failed due to reasons above!") from e

    else:
        module_logger().debug('No environment specified in hips dependencies. Taking %s environment...' % 'hips_full')
        subprocess_args = ['conda', 'env', 'create', '-q', '-f', 'hips_full.yml']  # ToDo: get rid of hardcoded stuff

        subcommand.run(subprocess_args)

    # set environment path
    environment_path = set_environment_path(active_hips)

    # update environment to fit hips needs
    install_hips_in_environment(active_hips)

    return environment_path


# ToDo: use explicit versioning of hips
def install_hips_in_environment(active_hips):
    """Installs the hips dependency in the environment

    Args:
        active_hips:
            The hips object to create a solution for.
    """
    environment_path = active_hips["_environment_path"]

    if not is_installed(environment_path, "hips", active_hips["min_hips_version"]):
        pip_install('git+https://gitlab.com/ida-mdc/hips.git', environment_path=environment_path)


def environment_exists(environment_name):
    """Checks whether an environment already exists or not.

    Args:
        environment_name:
            The name of the environment in which a solution will run.

    Returns:
        True when environment exists else false.
    """
    environment_dict = get_environment_dict()
    return True if environment_name in environment_dict.keys() else False


# todo: write tests
def get_active_environment_path():
    """Returns the environment form the active hips."""
    subprocess_args = [
        'conda', 'info', '--json'
    ]
    output = subprocess.check_output(subprocess_args).decode("utf-8")
    conda_list = json.loads(output)

    return conda_list["active_prefix"]


# ToDo: write tests
def pip_install(module, version=None, environment_name=None, environment_path=None):
    """Installs the given module int the an environment.

    Either this environment is given by name, or the current active
    environment is taken.

    Args:
        module:
            Either a path to a git or a package name.
        version:
            The version of the package to install. Must left unspecified if module points to a git.
        environment_name:
            The environment name to install the package to. The currently active one if none specified.
        environment_path:
            The environment path to install the package to. Ignores environment_name parameter when set.

    """
    if not environment_path:
        if environment_name:
            try:
                environment_path = get_environment_dict()[environment_name]
            except KeyError as e:
                raise RuntimeError("Environment name %s not found! Aborting..." % environment_name) from e
        else:
            environment_path = get_active_environment_path()

    if version:
        module = "==".join([module, version])

    # conda run necessary to correctly initialize pip
    subprocess_args = [
        'conda', 'run', '--no-capture-output', '--prefix',
        environment_path, 'pip', 'install', '-q', '--force-reinstall', module
    ]

    module_logger().debug("Installing %s in environment %s..." % (module, environment_path))
    subcommand.run(subprocess_args)
