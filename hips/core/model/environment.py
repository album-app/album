import json
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path

import validators
import yaml
from xdg import xdg_cache_home

from hips.core.model import logging
from hips.core.model.configuration import HipsDefaultValues
from hips.core.model.logging import hips_debug
from hips.core.utils import subcommand
from hips.core.utils.operations.file_operations import create_path_recursively, copy
from hips.core.utils.operations.url_operations import download_resource

module_logger = logging.get_active_logger


class Conda:

    @staticmethod
    def get_environment_dict():
        """Returns the conda environments available for the conda installation."""
        environment_dict = dict()

        conda_info = Conda.get_info()

        for env in conda_info["envs"]:
            environment_dict[os.path.basename(env)] = env

        return environment_dict

    @staticmethod
    def get_base_environment_path():
        conda_info = Conda.get_info()

        return conda_info["envs_dirs"][0]

    @staticmethod
    def environment_exists(environment_name):
        """Checks whether an environment already exists or not.

        Args:
            environment_name:
                The name of the environment in which a solution will run.

        Returns:
            True when environment exists else false.
        """
        environment_dict = Conda.get_environment_dict()
        return True if environment_name in environment_dict.keys() else False

    @staticmethod
    def get_active_environment_name():
        """Returns the environment form the active hips."""
        conda_list = Conda.get_info()
        return conda_list["active_prefix_name"]

    # todo: write tests
    @staticmethod
    def get_active_environment_path():
        """Returns the environment form the active hips."""
        conda_list = Conda.get_info()
        return conda_list["active_prefix"]

    @staticmethod
    def remove_environment(environment_name):
        if Conda.get_active_environment_name() == environment_name:
            module_logger().warning("Cannot remove active environment! Skipping...")
            return

        if not Conda.environment_exists(environment_name):
            module_logger().warning("Environment does not exist! Skipping...")
            return

        subprocess_args = [
            'conda', 'remove', '--all', '-y', '--json', '-n', environment_name
        ]

        subcommand.run(subprocess_args, log_output=False)

    @staticmethod
    def get_info():
        subprocess_args = [
            'conda', 'info', '--json'
        ]
        output = subcommand.check_output(subprocess_args)
        return json.loads(output)

    @staticmethod
    def list_environment(environment_path):
        subprocess_args = [
            'conda', 'list', '--json', '--prefix', environment_path,
        ]
        output = subcommand.check_output(subprocess_args)
        return json.loads(output)

    @staticmethod
    def is_installed(environment_path, module, version=None):
        res = Conda.list_environment(environment_path)
        for entry in res:
            if entry["name"] == module:
                if version:
                    if entry["version"] == version:
                        return True
                else:
                    return True
        return False

    @staticmethod
    def create_environment_from_file(yaml_path, environment_name):
        if Conda.environment_exists(environment_name):
            Conda.remove_environment(environment_name)

        if not (str(yaml_path).endswith(".yml") or str(yaml_path).endswith(".yaml")):
            raise NameError("File needs to be a yml or yaml file!")

        yaml_path = Path(yaml_path)

        if not (yaml_path.is_file() and yaml_path.stat().st_size > 0):
            raise ValueError("File not a valid yml file!")

        subprocess_args = ['conda', 'env', 'create', '--json', '-f', str(yaml_path)]

        try:
            subcommand.run(subprocess_args, log_output=False)
        except RuntimeError as e:
            # cleanup after failed installation
            if Conda.environment_exists(environment_name):
                module_logger().debug('Cleanup failed installation...')
                Conda.remove_environment(environment_name)
            raise RuntimeError("Command failed due to reasons above!") from e

    @staticmethod
    def create_environment(environment_name):
        if Conda.environment_exists(environment_name):
            Conda.remove_environment(environment_name)

        subprocess_args = ['conda', 'create', '--json', '-y', '-n', environment_name, 'python', 'pip']

        try:
            subcommand.run(subprocess_args, log_output=False)
        except RuntimeError as e:
            # cleanup after failed installation
            if Conda.environment_exists(environment_name):
                module_logger().debug('Cleanup failed installation...')
                Conda.remove_environment(environment_name)
            raise RuntimeError("Command failed due to reasons above!") from e

    @staticmethod
    def pip_install(environment_path, module):
        subprocess_args = [
            'conda', 'run', '--no-capture-output', '--prefix',
            environment_path, 'pip', 'install', '--force-reinstall', module
        ]

        subcommand.run(subprocess_args, log_output=False)

    @staticmethod
    def conda_install(environment_path, module):
        subprocess_args = [
            'conda', 'run', '--no-capture-output', '--prefix',
            environment_path, 'conda', 'install', '-y', module
        ]

        subcommand.run(subprocess_args, log_output=False)

    @staticmethod
    def run_script(environment_path, script_name):
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            # NOTE: WHEN USING 'CONDA RUN' THE CORRECT ENVIRONMENT GETS TEMPORARY ACTIVATED,
            # BUT THE PATH POINTS TO THE WRONG PYTHON (conda base folder python) BECAUSE THE CONDA BASE PATH
            # COMES FIRST IN ENVIRONMENT VARIABLE "%PATH%". THUS, FULL PATH IS NECESSARY TO CALL
            # THE CORRECT PYTHON OR PIP! ToDo: keep track of this!
            subprocess_args = [
                'conda', 'run', '--no-capture-output', '--prefix',
                environment_path, str(Path(environment_path).joinpath('python')), script_name
            ]
        else:
            subprocess_args = [
                'conda', 'run', '--no-capture-output', '--prefix',
                environment_path, 'python', script_name
            ]
        subcommand.run(subprocess_args)

    @staticmethod
    def cmd_available(environment_path, cmd):
        subprocess_args = [
            'conda', 'run', '--no-capture-output', '--prefix',
            environment_path
        ] + cmd
        try:
            subcommand.run(subprocess_args, log_output=False)
        except RuntimeError:
            return False

        return True


class Environment:

    def __init__(self, dependencies_dict, cache_name, cache_path):
        """Init routine

        Args:
            dependencies_dict:
                Can be None or hold the entries a) "environment_file" b) "environment_name"
            cache_name:
                name prefix for all files to cache
            cache_path:
                cache path
        """
        self.cache_path = Path(cache_path)
        self.cache_name = cache_name
        self.yaml_file = self.get_env_file(dependencies_dict)
        self.name = self.get_env_name(dependencies_dict)
        self.path = self.init_env_path()

    def install(self, min_hips_version=None):
        """Creates or updates an an environment and installs hips in the target environment."""
        self.create_or_update_env()
        self.path = self.get_env_path()

        self.install_hips(min_hips_version)

    def get_env_file(self, dependencies_dict):
        if dependencies_dict:
            if 'environment_file' in dependencies_dict:
                env_file = dependencies_dict['environment_file']

                yaml_path = self.cache_path.joinpath(
                    "%s%s" % (self.cache_name, ".yml"))
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
            return None
        return None

    def get_env_name(self, dependencies_dict):
        if dependencies_dict:
            if 'environment_name' in dependencies_dict:
                environment_name = dependencies_dict['environment_name']
                module_logger().debug('Environment name explicit given as: %s...' % environment_name)
                return environment_name

            elif 'environment_file' in dependencies_dict:
                environment_name = self.get_env_name_from_yaml()
                module_logger().debug('Extracted following name from file: %s...' %
                                      environment_name)
                return environment_name
            else:
                raise RuntimeError('No valid environment name or file specified! Don\'t know where to run solution!')
        else:
            environment_name = HipsDefaultValues.default_environment.value
            module_logger().debug('Environment name not given. Assume solution can be run in: %s...' % environment_name)
            return environment_name

    def get_env_name_from_yaml(self):
        """Reads out the "name" keywords from the environment yaml file

        Returns:
            The name of the environment.

        """
        module_logger().debug('Parsing environment name form yaml: %s...' % self.yaml_file)

        with open(self.yaml_file) as f:
            # todo: use safe_load to avoid code injection
            env = yaml.load(f, Loader=yaml.FullLoader)
        return env['name']

    def init_env_path(self):
        environment_dict = Conda.get_environment_dict()
        if self.name in environment_dict.keys():
            environment_path = environment_dict[self.name]
            module_logger().debug('Set environment path to %s...' % environment_path)

            return Path(environment_path)
        else:
            return None

    def get_env_path(self):
        env_path = self.init_env_path()
        if not env_path:
            raise RuntimeError('Could not find environment!')
        return env_path

    def is_installed(self, package_name, min_package_version=None):
        conda_list = Conda.list_environment(str(self.path))

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

    def run_script(self, script):
        """Runs the solution in the target environment

        Args:
            script:
                The script calling the solution
        """
        if not self.path:
            raise EnvironmentError("Environment \"%s\" not proper configured. Is the solution installed?" % self.name)

        module_logger().debug('run_in_environment: %s...' % str(self.path))

        # Use an environment path and a temporary file to store the script
        if hips_debug():
            fp = open(str(xdg_cache_home().joinpath('hips_test.py')), 'w')
            module_logger().debug("Executable file in: %s..." % str(xdg_cache_home().joinpath('hips_test.py')))
        else:
            fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            module_logger().debug('Executable file in: %s...' % fp.name)

        fp.write(script)
        fp.flush()
        os.fsync(fp)
        fp.close()

        Conda.run_script(str(self.path), fp.name)

        Path(fp.name).unlink()

    def create_or_update_env(self):
        if Conda.environment_exists(self.name):
            self.update()
        else:
            self.create()

    def update(self):
        module_logger().debug('Update environment %s...' % self.name)
        pass  # ToDo: implement

    def create(self):
        """Creates environment a solution runs in."""
        if self.yaml_file:
            Conda.create_environment_from_file(self.yaml_file, self.name)
        else:
            module_logger().warning("No yaml file specified. Creating Environment without dependencies!")
            Conda.create_environment(self.name)

    # ToDo: use explicit versioning of hips
    def install_hips(self, min_hips_version=None):
        """Installs the hips dependency in the environment"""
        if not Conda.cmd_available(str(self.path), ["git", "--version"]):
            Conda.conda_install(str(self.path), "git")

        if not self.is_installed("hips", min_hips_version):
            self.pip_install('git+https://gitlab.com/ida-mdc/hips.git')

    def pip_install(self, module, version=None):
        """Installs the given module int the an environment.

        Either this environment is given by name, or the current active
        environment is taken.

        Args:
            module:
                Either a path to a git or a package name.
            version:
                The version of the package to install. Must left unspecified if module points to a git.
        """

        if version:
            module = "==".join([module, version])

        module_logger().debug("Installing %s in environment %s..." % (module, str(self.path)))

        Conda.pip_install(str(self.path), module)

    def remove(self):
        Conda.remove_environment(self.name)
