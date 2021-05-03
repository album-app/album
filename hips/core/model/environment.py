import json
import os
import subprocess
import tempfile
from io import StringIO
from pathlib import Path

import validators
import yaml
from xdg import xdg_cache_home

from hips.core.model import logging
from hips.core.model.configuration import HipsConfiguration
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

    # todo: write tests
    @staticmethod
    def get_active_environment_path():
        """Returns the environment form the active hips."""
        conda_list = Conda.get_info()
        return conda_list["active_prefix"]

    @staticmethod
    def remove_environment(environment_name):
        subprocess_args = [
            'conda', 'remove', '--all', '-q', '-n', environment_name
        ]
        subprocess.run(subprocess_args)

    @staticmethod
    def get_info():
        subprocess_args = [
            'conda', 'info', '--json'
        ]
        output = subprocess.check_output(subprocess_args).decode("utf-8")
        return json.loads(output)

    @staticmethod
    def list_environment(environment_path):
        subprocess_args = [
            'conda', 'list', '--json', '--prefix', environment_path,
        ]
        output = subprocess.check_output(subprocess_args).decode("utf-8")
        return json.loads(output)

    @staticmethod
    def create_environment_from_file(yaml_path, environment_name):
        subprocess_args = ['conda', 'env', 'create', '-q', '-f', str(yaml_path)]

        try:
            subcommand.run(subprocess_args)
        except RuntimeError as e:
            # cleanup after failed installation
            if Conda.environment_exists(environment_name):
                module_logger().debug('Cleanup failed installation...')
                Conda.remove_environment(environment_name)
            raise RuntimeError("Command failed due to reasons above!") from e

    @staticmethod
    def create_environment(environment_name):
        subprocess_args = ['conda', 'create', '-q', '-n', environment_name, 'python', 'pip']

        try:
            subcommand.run(subprocess_args)
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
            environment_path, 'pip', 'install', '-q', '--force-reinstall', module
        ]
        subcommand.run(subprocess_args)

    @staticmethod
    def run_script(environment_path, script_name):
        subprocess_args = [
            'conda', 'run', '--no-capture-output', '--prefix',
            environment_path, 'python', script_name
        ]
        subcommand.run(subprocess_args)


class Environment:
    configuration = HipsConfiguration()
    yaml_file = ""
    name = ""
    path = ""

    def __init__(self, active_hips):
        self.yaml_file = self.get_env_file(active_hips)
        self.name = self.get_env_name(active_hips)

    def install(self, min_hips_version=None):
        """Creates or updates an anvironment and installs hips in the target environment."""
        self.create_or_update_env()
        self.path = self.get_env_path()

        self.install_hips(min_hips_version)

    def get_env_file(self, active_hips):
        """Sets the yaml_path attribute."""
        if 'dependencies' in dir(active_hips):
            if 'environment_file' in active_hips.dependencies:
                env_file = active_hips.dependencies['environment_file']

                yaml_path = self.configuration.get_cache_path_hips(active_hips).joinpath(
                    "%s%s" % (active_hips.name, ".yml"))
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

    def get_env_name(self, active_hips):
        if hasattr(active_hips, "dependencies"):
            if 'environment_name' in active_hips.dependencies:
                environment_name = active_hips.dependencies['environment_name']
                module_logger().debug('Environment name explicit given as: %s...' % environment_name)
                return environment_name

            elif 'environment_file' in active_hips.dependencies:
                environment_name = self.get_environment_name_from_yaml()
                module_logger().debug('Extracted following name from file: %s...' %
                                      environment_name)
                return environment_name
            else:
                raise RuntimeError('No valid environment name or file specified! Don\'t know where to run solution!')
        else:
            environment_name = 'hips'
            module_logger().debug('Environment name not given. Assume solution can be run in: %s...' % environment_name)
            return environment_name

    def get_environment_name_from_yaml(self):
        """Reads out the "name" keywords from the environment yaml file

        Returns:
            The name of the environment.

        """
        module_logger().debug('Parsing environment name form yaml: %s...' % self.yaml_file)

        with open(self.yaml_file) as f:
            # todo: use safe_load to avoid code injection
            env = yaml.load(f, Loader=yaml.FullLoader)
        return env['name']

    def get_env_path(self):
        environment_dict = Conda.get_environment_dict()
        if self.name in environment_dict.keys():
            environment_path = environment_dict[self.name]
            module_logger().debug('Set environment path to %s...' % environment_path)

            return environment_path
        else:
            raise RuntimeError('Could not find environment!')

    # todo: write tests
    def is_installed(self, package_name, min_package_version=None):
        conda_list = Conda.list_environment(self.path)

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
        module_logger().debug('run_in_environment: %s...' % self.path)

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

        Conda.run_script(self.path, fp.name)

        fp.close()

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
        """Installs the hips dependency in the environment

        Args:
            active_hips:
                The hips object to create a solution for.
        """

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

        module_logger().debug("Installing %s in environment %s..." % (module, self.path))

        Conda.pip_install(self.path, module)

    def remove(self):
        Conda.remove_environment(self.name)
