import os
import tempfile
from io import StringIO
from pathlib import Path

import validators
import yaml

from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.conda import Conda
from hips.core.utils.operations.file_operations import create_path_recursively, copy
from hips.core.utils.operations.url_operations import download_resource
from hips_runner import logging
from hips_runner.logging import hips_debug

module_logger = logging.get_active_logger


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
            fp = open(str(HipsDefaultValues.app_cache_dir.value.joinpath('hips_test.py')), 'w')
            module_logger().debug("Executable file in: %s..." % str(HipsDefaultValues.app_cache_dir.value.joinpath('hips_test.py')))
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

        if not self.is_installed("hips-runner", min_hips_version):
            self.pip_install('git+https://gitlab.com/ida-mdc/hips-runner.git')

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
