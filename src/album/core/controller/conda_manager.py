import json
import os
import sys
import tempfile
from pathlib import Path

from album.core import Solution
from album.core.model.default_values import DefaultValues

from album.runner.logging import debug_settings

from album.core.model.environment import Environment

from album.core.concept.singleton import Singleton
from album.core.model.configuration import Configuration
from album.core.utils import subcommand
from album.core.utils.operations.file_operations import force_remove
from album.runner import logging

module_logger = logging.get_active_logger


class CondaManager(metaclass=Singleton):
    """Class for handling conda environments.

    The conda class manages the environments a solution is supposed to run in. It provides all features necessary for
    environment creation, deletion, dependency installation, etc.

    Notes:
        An installed \"conda\" program must be available and callable via commandline or powershell.

    """
    # singletons
    configuration = None

    def __init__(self):
        self.configuration = Configuration()
        self.conda_executable = self.configuration.conda_executable

    def get_environment_dict(self):
        """Returns the conda environments available for the conda installation."""
        environment_dict = dict()

        conda_info = self.get_info()

        for env in conda_info["envs"]:
            environment_dict[os.path.basename(env)] = env

        return environment_dict

    def get_base_environment_path(self):
        """Gets the first of the paths the conda installation uses to manage its environments."""
        conda_info = self.get_info()

        return conda_info["envs_dirs"][0]

    def environment_exists(self, environment_name):
        """Checks whether an environment already exists or not.

        Args:
            environment_name:
                The name of the environment in which a solution will run.

        Returns:
            True when environment exists else false.
        """
        environment_dict = self.get_environment_dict()
        return True if environment_name in environment_dict.keys() else False

    def get_environment_path(self, environment_name: str):
        """Gets the environment path for a given environment

        Args:
            environment:
                The environment to get the path for.

        Returns:
            None or the path
        """
        environment_dict = self.get_environment_dict()
        path = environment_dict[environment_name] if environment_name in environment_dict.keys() else None
        if not path:
            raise RuntimeError('Could not find environment %s.' % environment_name)
        return path

    def get_active_environment_name(self):
        """Returns the environment form the active album."""
        conda_list = self.get_info()
        return conda_list["active_prefix_name"]

    def get_active_environment_path(self):
        """Returns the environment form the active album."""
        conda_list = self.get_info()
        return conda_list["active_prefix"]

    def remove_environment(self, environment_name, timeout1=60, timeout2=120):
        """Removes an environment given its name. Does nothing when environment does not exist.

        Args:
            environment_name:
                The name of the environment to remove
            timeout1:
                Timeout in seconds, after which a rescue operation (linebreak input) is send to the
                process running the operation. Timeout is resets each time a feedback is passed to the main process.
            timeout2:
                Timeout in seconds after timeout1 passed, after which the process behind the
                operation is declared dead. Timeout is resets each time a feedback is passed to the main process.

        """
        if self.get_active_environment_name() == environment_name:
            module_logger().warning("Cannot remove active environment! Skipping...")
            return

        if not self.environment_exists(environment_name):
            module_logger().warning("Environment does not exist! Skipping...")
            return

        path = self.get_environment_path(environment_name)

        subprocess_args = [
            self.conda_executable, 'env', 'remove', '-y', '--json', '-n', environment_name
        ]

        subcommand.run(subprocess_args, log_output=False, timeout1=timeout1, timeout2=timeout2)

        # try to remove file content if any but don't fail:
        force_remove(path)

    def get_info(self):
        """Get the info of the conda installation on the corresponding system.

        Returns:
            dictionary corresponding to conda info.
        """
        subprocess_args = [
            self.conda_executable, 'info', '--json'
        ]
        output = subcommand.check_output(subprocess_args)
        return json.loads(output)

    def list_environment(self, environment_path):
        """Lists all available conda installation in the given environment.

        Args:
            environment_path:
                The prefix of the environment to list.

        Returns:
            dictionary containing the available packages in the given conda environment.
        """
        subprocess_args = [
            self.conda_executable, 'list', '--json', '--prefix', environment_path,
        ]
        output = subcommand.check_output(subprocess_args)
        return json.loads(output)

    def create_environment_from_file(self, yaml_path, environment_name, timeout1=60, timeout2=120):
        """Creates a conda environment given a path to a yaml file and its name.

        Args:
            yaml_path:
                The path to the file.
            environment_name:
                The name of the environment. Must be the same as specified in the yml file.
            timeout1:
                Timeout in seconds, after which a rescue operation (linebreak input) is send to the
                process running the operation. Timeout is resets each time a feedback is passed to the main process.
            timeout2:
                Timeout in seconds after timeout1 passed, after which the process behind the
                operation is declared dead. Timeout is resets each time a feedback is passed to the main process.

        Raises:
            NameError:
                When the file has the wrong format according to its extension.
            ValueError:
                When the file is unreadable or empty.
            RuntimeError:
                When the environment could not be created due to whatever reasons.

        """
        if self.environment_exists(environment_name):
            self.remove_environment(environment_name)

        if not (str(yaml_path).endswith(".yml") or str(yaml_path).endswith(".yaml")):
            raise NameError("File needs to be a yml or yaml file!")

        yaml_path = Path(yaml_path)

        if not (yaml_path.is_file() and yaml_path.stat().st_size > 0):
            raise ValueError("File not a valid yml file!")

        subprocess_args = [self.conda_executable, 'env', 'create', '--json', '-f', str(yaml_path)]

        try:
            subcommand.run(subprocess_args, log_output=False, timeout1=timeout1, timeout2=timeout2)
        except RuntimeError as e:
            # cleanup after failed installation
            if self.environment_exists(environment_name):
                module_logger().debug('Cleanup failed installation...')
                self.remove_environment(environment_name)
            raise RuntimeError("Command failed due to reasons above!") from e

    def create_environment(self, environment_name, timeout1=60, timeout2=120, force=False):
        """Creates a conda environment with python (latest version) installed.

        Args:
            environment_name:
                The desired environment name.
            timeout1:
                Timeout in seconds, after which a rescue operation (linebreak input) is send to the
                process running the operation. Timeout is resets each time a feedback is passed to the main process.
            timeout2:
                Timeout in seconds after timeout1 passed, after which the process behind the
                operation is declared dead. Timeout is resets each time a feedback is passed to the main process.
            force:
                If True, force creates the environment by deleting the old one.
        Raises:
            RuntimeError:
                When the environment could not be created due to whatever reasons.

        """
        env_exists = self.environment_exists(environment_name)
        if force and env_exists:
            self.remove_environment(environment_name)
        else:
            if env_exists:
                raise FileExistsError("Environment already exists!")

        subprocess_args = [
            self.conda_executable, 'create', '--force', '--json', '-y', '-n', environment_name, 'python=3.6', 'pip'
        ]

        try:
            subcommand.run(subprocess_args, log_output=False, timeout1=timeout1, timeout2=timeout2)
        except RuntimeError as e:
            # cleanup after failed installation
            if self.environment_exists(environment_name):
                module_logger().debug('Cleanup failed installation...')
                self.remove_environment(environment_name)
            raise RuntimeError("Command failed due to reasons above!") from e

    def pip_install(self, environment_path, module, timeout1=60, timeout2=120):
        """Installs a package in the given environment via pip.

        Args:
            environment_path:
                The prefix path of the environment to install the package to.
            module:
                The module or package name.
            timeout1:
                Timeout in seconds, after which a rescue operation (linebreak input) is send to the
                process running the operation. Timeout is resets each time a feedback is passed to the main process.
            timeout2:
                Timeout in seconds after timeout1 passed, after which the process behind the
                operation is declared dead. Timeout is resets each time a feedback is passed to the main process.
        """
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            # NOTE: WHEN USING 'CONDA RUN' THE CORRECT ENVIRONMENT GETS TEMPORARY ACTIVATED,
            # BUT THE PATH POINTS TO THE WRONG PIP (conda base folder + Scripts + pip) BECAUSE THE CONDA BASE PATH
            # COMES FIRST IN ENVIRONMENT VARIABLE "%PATH%". THUS, FULL PATH IS NECESSARY TO CALL
            # THE CORRECT PYTHON OR PIP! ToDo: keep track of this!
            subprocess_args = [
                self.conda_executable, 'run', '--no-capture-output', '--prefix',
                environment_path, str(Path(environment_path).joinpath('python')), '-m', 'pip', 'install',
                '--no-warn-conflicts', module
            ]
        else:
            subprocess_args = [
                self.conda_executable, 'run', '--no-capture-output', '--prefix',
                environment_path, 'python', '-m', 'pip', 'install', '--no-warn-conflicts', module
            ]

        subcommand.run(subprocess_args, log_output=False, timeout1=timeout1, timeout2=timeout2)

    def conda_install(self, environment, module, timeout1=60, timeout2=120):
        """Installs a package in the given environment via conda.

        Args:
            environment:
                The environment to install the package into.
            module:
                The module or package name.
            timeout1:
                Timeout in seconds, after which a rescue operation (linebreak input) is send to the
                process running the operation. Timeout is resets each time a feedback is passed to the main process.
            timeout2:
                Timeout in seconds after timeout1 passed, after which the process behind the
                operation is declared dead. Timeout is resets each time a feedback is passed to the main process.

        """
        subprocess_args = [
            self.conda_executable, 'install', '--prefix',
            environment.path, '-y', module
        ]

        subcommand.run(subprocess_args, log_output=False, timeout1=timeout1, timeout2=timeout2)

    def run_script(self, environment_path, script_full_path, timeout1=60, timeout2=120):
        """Runs a script in the given environment.

        Args:
            environment_path:
                The prefix path of the environment to install the package to.
            script_full_path:
                The full path to the script to run.
            timeout1:
                Timeout in seconds, after which a rescue operation (linebreak input) is send to the
                process running the operation. Timeout is resets each time a feedback is passed to the main process.
            timeout2:
                Timeout in seconds after timeout1 passed, after which the process behind the
                operation is declared dead. Timeout is resets each time a feedback is passed to the main process.

        """
        if sys.platform == 'win32' or sys.platform == 'cygwin':
            # NOTE: WHEN USING 'CONDA RUN' THE CORRECT ENVIRONMENT GETS TEMPORARY ACTIVATED,
            # BUT THE PATH POINTS TO THE WRONG PYTHON (conda base folder python) BECAUSE THE CONDA BASE PATH
            # COMES FIRST IN ENVIRONMENT VARIABLE "%PATH%". THUS, FULL PATH IS NECESSARY TO CALL
            # THE CORRECT PYTHON OR PIP! ToDo: keep track of this!
            subprocess_args = [
                self.conda_executable, 'run', '--no-capture-output', '--prefix',
                environment_path, str(Path(environment_path).joinpath('python')), script_full_path
            ]
        else:
            subprocess_args = [
                self.conda_executable, 'run', '--no-capture-output', '--prefix',
                environment_path, 'python', script_full_path
            ]
        subcommand.run(subprocess_args, timeout1=timeout1, timeout2=timeout2)

    def cmd_available(self, environment_path, cmd):
        """Checks whether a command is available when running the command in the given environment.

        Args:
            environment_path:
                The prefix path of the environment.
            cmd:
                The command to check for.

        Returns:
            True when exit status of the command is 0, else False.

        """
        subprocess_args = [
                              self.conda_executable, 'run', '--no-capture-output', '--prefix',
                              environment_path
                          ] + cmd
        try:
            subcommand.run(subprocess_args, log_output=False, timeout1=10, timeout2=10)
        except RuntimeError:
            return False

        return True

    def set_environment_path(self, environment: Environment):
        path = self.get_environment_path(environment.name)
        module_logger().debug('Set environment path to %s...' % path)
        environment.path = path

    def is_installed(self, environment_path: str, package_name, min_package_version=None):
        """Checks if package is installed in a certain version."""
        conda_list = self.list_environment(str(environment_path))

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

    def run_scripts(self, environment: Environment, scripts):
        """Runs the solution in the target environment

        Args:
            scripts:
                List of he scripts calling the solution(s)
            environment:
                The virtual environment used to run the scripts
        """
        if not environment.path:
            raise EnvironmentError('Could not find environment %s. Is the solution installed?' % environment.name)

        module_logger().debug('run_in_environment: %s...' % str(environment.path))

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

        self.run_script(str(environment.path), fp.name)

        Path(fp.name).unlink()

    def create_or_update_env(self, environment: Environment):
        """Creates or updates the environment"""
        if self.environment_exists(environment.name):
            self.update(environment)
        else:
            self.create(environment)

    def update(self, environment: Environment):
        """Updates the environment"""
        module_logger().debug('Update environment %s...' % environment.name)
        pass  # ToDo: implement

    def create(self, environment: Environment):
        """Creates environment a solution runs in."""
        if environment.yaml_file:
            self.create_environment_from_file(environment.yaml_file, environment.name)
        else:
            module_logger().warning("No yaml file specified. Creating Environment without dependencies!")
            self.create_environment(environment.name)

    def install(self, environment: Environment, min_album_version=None):
        """Creates or updates an an environment and installs album in the target environment."""
        self.create_or_update_env(environment)
        self.set_environment_path(environment)
        self.install_framework(environment.path, min_album_version)

    # ToDo: use explicit versioning of album
    def install_framework(self, environment_path: str, min_framework_version=None):
        """Installs the album dependency in the environment"""

        if not self.is_installed(environment_path, "album-runner", min_framework_version):
            self.pip_install_into_environment(environment_path, DefaultValues.runner_url.value)

    def pip_install_into_environment(self, environment_path: str, module, version=None):
        """Installs the given module in the environment.

        Either this environment is given by name, or the current active
        environment is taken.

        Args:
            environment_path:
                The virtual environment path to install to.
            module:
                Either a path to a git or a package name.
            version:
                The version of the package to install. Must left unspecified if module points to a git.
        """

        if version:
            module = "==".join([module, version])

        module_logger().debug("Installing %s in environment %s..." % (module, str(environment_path)))

        self.pip_install(str(environment_path), module)
