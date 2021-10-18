import os
import tempfile
from io import StringIO
from pathlib import Path

import validators

from album.core.controller.conda_manager import CondaManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import create_path_recursively, copy, write_dict_to_yml, \
    get_dict_from_yml
from album.core.utils.operations.url_operations import download_resource
from album.runner import logging
from album.runner.logging import debug_settings

module_logger = logging.get_active_logger


class Environment:
    """Class managing an environment a solution lives in.

    Each solution lives in its own environment having different dependencies. These can be libraries, programs, etc.
    Each environment has its own environment path and is identified by such. Each album environment has to have
    the album-runner installed for the album framework to be able to run the solution in its environment.
    An environment can be set up by environment file or only by name.

    """

    def __init__(self, dependencies_dict, environment_name, cache_path):
        """Init routine

        Args:
            dependencies_dict:
                Can be None or hold the entries a) "environment_file" b) "environment_name"
            environment_name:
                name prefix for all files to cache.
                Used when "name" is not available during yaml-file download for example.
            cache_path:
                cache path where to store downloads (yaml file, etc.)
        """
        self.conda = CondaManager()
        self.name = environment_name
        self.cache_path = Path(cache_path)
        self.yaml_file = self.prepare_env_file(dependencies_dict)
        self.path = self.init_env_path()

    def install(self, min_album_version=None):
        """Creates or updates an an environment and installs album in the target environment."""
        self.create_or_update_env()
        self.path = self.get_env_path()

        self.install_framework(min_album_version)

    def prepare_env_file(self, dependencies_dict):
        """Checks how to set up an environment. Returns a path to a valid yaml file. Environment name in that file
        will be overwritten!

        Args:
            dependencies_dict:
                Dictionary holding the "environment_file" key. Environment file can be:
                    - url
                    - path
                    - stream object

        Returns:
            Path to a valid yaml file where environment name has been replaced!

        """
        if dependencies_dict:
            if 'environment_file' in dependencies_dict:
                env_file = dependencies_dict['environment_file']

                yaml_path = self.cache_path.joinpath(
                    "%s%s" % (self.name, ".yml"))
                create_path_recursively(yaml_path.parent)

                if isinstance(env_file, str):
                    # case valid url
                    if validators.url(env_file):
                        yaml_path = download_resource(env_file, yaml_path)
                    # case Path
                    elif Path(env_file).is_file() and Path(env_file).stat().st_size > 0:
                        yaml_path = copy(env_file, yaml_path)
                    else:
                        raise TypeError("Yaml file must either be a url to a valid file"
                                        " or point to a file on the disk!")
                # case String stream
                elif isinstance(env_file, StringIO):
                    with open(yaml_path, "w+") as f:
                        env_file.seek(0)  # make sure we start from the beginning
                        f.writelines(env_file.readlines())
                    yaml_path = yaml_path
                else:
                    raise RuntimeError('Environment file specified, but format is unknown!'
                                       ' Don\'t know where to run solution!')

                yaml_dict = get_dict_from_yml(yaml_path)
                yaml_dict["name"] = self.name
                write_dict_to_yml(yaml_path, yaml_dict)

                return yaml_path
            return None
        return None

    def init_env_path(self):
        """Sets the environment path from the name of the environment

        Returns:
            The prefix path of the environment.

        """
        environment_dict = self.conda.get_environment_dict()
        if self.name in environment_dict.keys():
            environment_path = environment_dict[self.name]
            module_logger().debug('Set environment path to %s...' % environment_path)

            return Path(environment_path)
        else:
            return None

    def get_env_path(self):
        """Gets the environment path prefix. Raises error if not set """
        env_path = self.init_env_path()
        if not env_path:
            raise RuntimeError('Could not find environment!')
        return env_path

    def is_installed(self, package_name, min_package_version=None):
        """Checks if package is installed in a certain version."""
        conda_list = self.conda.list_environment(str(self.path))

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

    def run_scripts(self, scripts):
        """Runs the solution in the target environment

        Args:
            scripts:
                List of he scripts calling the solution(s)
        """
        if not self.path:
            raise EnvironmentError("Environment \"%s\" not proper configured. Is the solution installed?" % self.name)

        module_logger().debug('run_in_environment: %s...' % str(self.path))

        # Use an environment path and a temporary file to store the script
        if debug_settings():
            fp = open(str(DefaultValues.app_cache_dir.value.joinpath('album_test.py')), 'w')
            module_logger().debug(
                "Executable file in: %s..." % str(DefaultValues.app_cache_dir.value.joinpath('album_test.py')))
        else:
            fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            module_logger().debug('Executable file in: %s...' % fp.name)

        # first write scripts to disc, create meta-script to execute them in the order of the list
        if len(scripts) > 1:
            script = ""
            for s in scripts:
                fp_step = tempfile.NamedTemporaryFile(mode='w+', delete=False)
                fp_step.write(s)
                fp_step.flush()
                os.fsync(fp_step)
                script += "\nexec(open(r\'%s\').read())\n" % fp_step.name
                fp_step.close()
        else:
            script = scripts[0]

        fp.write(script)
        fp.flush()
        os.fsync(fp)
        fp.close()

        self.conda.run_script(str(self.path), fp.name)

        Path(fp.name).unlink()

    def create_or_update_env(self):
        """Creates or updates the environment"""
        if self.conda.environment_exists(self.name):
            self.update()
        else:
            self.create()

    def update(self):
        """Updates the environment"""
        module_logger().debug('Update environment %s...' % self.name)
        pass  # ToDo: implement

    def create(self):
        """Creates environment a solution runs in."""
        if self.yaml_file:
            self.conda.create_environment_from_file(self.yaml_file, self.name)
        else:
            module_logger().warning("No yaml file specified. Creating Environment without dependencies!")
            self.conda.create_environment(self.name)

    # ToDo: use explicit versioning of album
    def install_framework(self, min_framework_version=None):
        """Installs the album dependency in the environment"""
        if not self.is_installed("album-runner", min_framework_version):
            self.pip_install(DefaultValues.runner_url.value)

    def pip_install(self, module, version=None):
        """Installs the given module in the environment.

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

        self.conda.pip_install(str(self.path), module)

    def remove(self):
        """Removes the environment"""
        self.conda.remove_environment(self.name)