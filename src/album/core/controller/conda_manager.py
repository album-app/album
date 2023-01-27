import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from packaging import version

from album.core.api.model.configuration import IConfiguration
from album.core.api.model.environment import IEnvironment
from album.core.model.default_values import DefaultValues
from album.core.model.link import Link
from album.core.utils import subcommand
from album.core.utils.operations.file_operations import (
    construct_cache_link_target,
    remove_link, force_remove,
)
from album.core.utils.subcommand import SubProcessError
from album.runner import album_logging
from album.runner.album_logging import debug_settings

module_logger = album_logging.get_active_logger


class CondaManager:
    """Class for handling conda environments.

    The conda class manages the environments a solution is supposed to run in. It provides all features necessary for
    environment creation, deletion, dependency installation, etc.

    Notes:
        An installed \"conda\" program must be available and callable via commandline or powershell.

    """

    def __init__(self, configuration: IConfiguration):
        self._configuration = configuration
        self._conda_executable = self._configuration.conda_executable()

    def _get_install_environment_executable(self):
        return self._conda_executable

    @staticmethod
    def check_for_executable():
        try:
            subprocess.run([DefaultValues.conda_path.value], capture_output=True)
            return True
        except FileNotFoundError:
            return False

    def get_environment_list(self):
        """Returns the available album conda environments."""
        if Path(self._get_base_environment_target_path()).exists():
            return sorted(
                self._get_immediate_subdirectories(
                    self._get_base_environment_target_path()
                )
            )
        else:
            return []

    @staticmethod
    def _get_immediate_subdirectories(a_dir: Path):
        return [
            a_dir.joinpath(name).resolve()
            for name in os.listdir(str(a_dir))
            if os.path.isdir(os.path.join(str(a_dir), name))
        ]

    def _get_base_environment_target_path(self):
        """Gets the first of the paths the conda installation uses to manage its environments."""
        return Path(self._configuration.lnk_path()).joinpath(
            DefaultValues.lnk_env_prefix.value
        )

    def environment_exists(self, environment_name):
        """Checks whether an environment already exists or not.

        Args:
            environment_name:
                The name of the environment in which a solution will run.

        Returns:
            True when environment exists else false.
        """
        environment_list = self.get_environment_list()
        path_expected = self._environment_name_to_path(environment_name, create=False)

        return (
            True
            if (
                path_expected
                and path_expected.resolve() in environment_list
                and os.listdir(path_expected)
            )
            else False
        )

    def _environment_name_to_path(self, environment_name, create=True):
        path = os.path.normpath(
            self._configuration.environments_path().joinpath(environment_name)
        )
        target = construct_cache_link_target(
            self._configuration.lnk_path(),
            point_from=path,
            point_to=DefaultValues.lnk_env_prefix.value,
            create=create,
        )
        if target:
            return Link(target).set_link(path)
        else:
            return None

    def get_environment_path(self, environment_name: str, create: bool = True) -> Link:
        """Gets the environment path for a given environment

        Args:
            environment_name:
                The environment to get the path for.
            create:



        Returns:
            None or the path
        """
        environment_list = self.get_environment_list()
        path_expected = self._environment_name_to_path(environment_name, create)

        if path_expected.resolve() in environment_list:
            return path_expected
        raise LookupError("Could not find environment %s." % environment_name)

    def get_active_environment_name(self):
        """Returns the environment from the active album."""
        environment_info = self.get_info()
        return environment_info["active_prefix_name"]

    def get_active_environment_path(self):
        """Returns the environment form the active album."""
        environment_info = self.get_info()
        path = environment_info["active_prefix"]
        link = construct_cache_link_target(
            self._configuration.lnk_path(),
            point_from=path,
            point_to=DefaultValues.lnk_env_prefix.value,
            create=False,
        )
        if link:
            return link
        else:
            return Link(path)

    def remove_environment(self, environment_name) -> bool:
        """Removes an environment given its name. Does nothing when environment does not exist.

        Args:
            environment_name:
                The name of the environment to remove

        Returns:
            True, when removal succeeded, else False

        """
        if self.get_active_environment_name() == environment_name:
            module_logger().warning("Cannot remove active environment! Skipping...")
            return False

        if not self.environment_exists(environment_name):
            module_logger().warning("Environment does not exist! Skipping...")
            return False

        path = self.get_environment_path(environment_name, create=False)

        try:
            subprocess_args = self._get_remove_env_args(path)
            subcommand.run(subprocess_args, log_output=False)
        except SubProcessError:
            module_logger().debug(
                "Can't delete environment via command line call, deleting the folder next..."
            )
        # try to remove file content if any but don't fail:
        remove_link(path)
        return True

    def get_info(self):
        """Get the info of the conda installation on the corresponding system.

        Returns:
            dictionary corresponding to conda info.
        """
        subprocess_args = [self._get_install_environment_executable(), "info", "--json"]
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
            self._get_install_environment_executable(),
            "list",
            "--json",
            "--prefix",
            str(environment_path),
        ]
        output = subcommand.check_output(subprocess_args)
        return json.loads(output)

    def create_environment_from_file(
        self, yaml_path, environment_name, album_api_version=None
    ):
        """Creates a conda environment given a path to a yaml file and its name.

        Args:
            yaml_path:
                The path to the file.
            environment_name:
                The name of the environment. Must be the same as specified in the yml file.
            album_api_version:
                The api version (runner version) in the environment.

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

        with open(yaml_path, "r") as f:
            content = yaml.safe_load(f)

        self._append_runner_and_install(album_api_version, environment_name, content)

    @staticmethod
    def _append_framework_to_yml(content, album_api_version):
        if version.parse(album_api_version) >= version.parse(
            DefaultValues.first_runner_conda_version.value
        ):
            return CondaManager._append_framework_via_conda_to_yml(
                content, album_api_version
            )
        else:
            return CondaManager._append_framework_via_pip_to_yml(
                content, album_api_version
            )

    @staticmethod
    def _append_framework_via_conda_to_yml(content, album_api_version):
        framework = "conda-forge::%s=%s" % (
            DefaultValues.runner_api_packet_name.value,
            album_api_version,
        )
        if not "dependencies" in content or not content["dependencies"]:
            content["dependencies"] = []
        content["dependencies"].append(framework)
        return content

    @staticmethod
    def _append_framework_via_pip_to_yml(content, album_api_version):
        # There might be environments without pip, so the the dependency content needs
        # to be adjusted to make sure pip is available.
        framework = "%s==%s" % (
            DefaultValues.runner_api_packet_name.value,
            album_api_version,
        )
        if not "dependencies" in content or not content["dependencies"]:
            content["dependencies"] = []
        pip_dict = None
        found_pip_dep = False
        for dep in content["dependencies"]:
            if isinstance(dep, dict):
                if "pip" in dep:
                    pip_dict = dep
            if dep == "pip" or str(dep).startswith("pip="):
                found_pip_dep = True
        if not found_pip_dep:
            content["dependencies"].append(DefaultValues.runner_pip_version.value)
        if not pip_dict:
            pip_dict = {"pip": []}
            content["dependencies"].append(pip_dict)
        pip_dict["pip"].append(framework)
        return content

    def create_environment(self, environment_name, album_api_version=None, force=False):
        """Creates a conda environment with python (latest version) installed.

        Args:
            environment_name:
                The desired environment name.
            force:
                If True, force creates the environment by deleting the old one.
            album_api_version:
                The api version (runner version) in the environment.

        Raises:
            RuntimeError:
                When the environment could not be created due to whatever reasons.

        """
        env_exists = self.environment_exists(environment_name)
        if force and env_exists:
            self.remove_environment(environment_name)
        else:
            if env_exists:
                raise EnvironmentError(
                    "Environment with name %s already exists!" % environment_name
                )

        env_content = {
            "channels": ["defaults"],
            "dependencies": [
                "python=%s" % DefaultValues.default_solution_python_version.value
            ],
        }

        self._append_runner_and_install(
            album_api_version, environment_name, env_content
        )

    def _append_runner_and_install(
        self, album_api_version, environment_name, environment_content
    ):

        if not album_api_version:
            album_api_version = DefaultValues.runner_api_packet_version.value

        environment_content = self._append_framework_to_yml(
            environment_content, album_api_version
        )
        env_prefix = os.path.normpath(self._environment_name_to_path(environment_name))
        force_remove(env_prefix)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".yml"
        ) as env_file:

            env_file.write(yaml.safe_dump(environment_content))
        subprocess_args = self._get_env_create_args(env_file, env_prefix)
        try:
            subcommand.run(subprocess_args, log_output=True)
        except RuntimeError as e:
            # cleanup after failed installation
            if self.environment_exists(environment_name):
                module_logger().debug("Cleanup failed environment creation...")
                self.remove_environment(environment_name)
            raise RuntimeError("Command failed due to reasons above!") from e
        finally:
            os.remove(env_file.name)

    def _get_env_create_args(self, env_file, env_prefix):
        subprocess_args = [
            self._get_install_environment_executable(),
            "env",
            "create",
            "--force",
            "--file",
            env_file.name,
            "-p",
            env_prefix,
        ]
        return subprocess_args

    def _get_run_script_args(self, environment_path, script_full_path):
        if sys.platform == "win32" or sys.platform == "cygwin":
            # NOTE: WHEN USING 'CONDA RUN' THE CORRECT ENVIRONMENT GETS TEMPORARY ACTIVATED,
            # BUT THE PATH POINTS TO THE WRONG PYTHON (conda base folder python) BECAUSE THE CONDA BASE PATH
            # COMES FIRST IN ENVIRONMENT VARIABLE "%PATH%". THUS, FULL PATH IS NECESSARY TO CALL
            # THE CORRECT PYTHON OR PIP! ToDo: keep track of this!
            subprocess_args = [
                self._conda_executable,
                "run",
                "--no-capture-output",
                "--prefix",
                os.path.normpath(environment_path),
                os.path.normpath(Path(environment_path).joinpath("python")),
                os.path.normpath(script_full_path),
            ]
        else:
            subprocess_args = [
                self._conda_executable,
                "run",
                "--no-capture-output",
                "--prefix",
                os.path.normpath(environment_path),
                "python",
                "-u",
                os.path.normpath(script_full_path),
            ]
        return subprocess_args

    def _get_remove_env_args(self, path):
        subprocess_args = [
            self._get_install_environment_executable(),
            "env",
            "remove",
            "-y",
            "-q",
            "-p",
            os.path.normpath(path),
        ]
        return subprocess_args

    def run_script(self, environment_path, script_full_path, pipe_output=True):
        """Runs a script in the given environment.

        Args:
            environment_path:
                The prefix path of the environment to install the package to.
            script_full_path:
                The full path to the script to run.
            pipe_output:
                Indicates whether to pipe the output of the subprocess or just return it as is.

        """
        subprocess_args = self._get_run_script_args(environment_path,script_full_path)
        subcommand.run(subprocess_args, pipe_output=pipe_output)

    def set_environment_path(self, environment: IEnvironment):
        path = self.get_environment_path(environment.name())
        module_logger().debug("Set environment path to %s..." % path)
        environment.set_path(path)

    def is_installed(
        self, environment_path: str, package_name, min_package_version=None
    ):
        """Checks if package is installed in a certain version."""
        conda_list = self.list_environment(environment_path)

        for package in conda_list:
            if package["name"] == package_name:
                if min_package_version:
                    if package["version"] == min_package_version:
                        module_logger().debug(
                            "Package %s:%s is installed..."
                            % (package_name, min_package_version)
                        )
                        return True
                    if package["version"] < min_package_version:
                        module_logger().debug(
                            "Package %s:%s is installed. Requirements not set! Reinstalling..."
                            % (package_name, package["version"])
                        )
                        return False
                    if package["version"] > min_package_version:
                        module_logger().debug(
                            "Package %s:%s is installed. Version should be compatible..."
                            % (package_name, package["version"])
                        )
                        return True
                else:
                    module_logger().debug(
                        "Package %s:%s is installed..."
                        % (package_name, package["version"])
                    )
                    return True

        return False

    def run_scripts(self, environment: IEnvironment, scripts, pipe_output=True):
        """Runs the solution in the target environment

        Args:
            scripts:
                List of he scripts calling the solution(s)
            environment:
                The virtual environment used to run the scripts
            pipe_output:
                Indicates whether to pipe the output of the subprocess or just return it as is.
        """
        if not environment.path():
            raise EnvironmentError(
                "Could not find environment %s. Is the solution installed?"
                % environment.name()
            )

        module_logger().debug("run_in_environment: %s..." % str(environment.path()))

        # first write scripts to disc, create meta-script to execute them in the order of the list
        if len(scripts) > 1:
            script = ""
            for s in scripts:
                fp_step = tempfile.NamedTemporaryFile(mode="w+", delete=False)
                fp_step.write(s)
                fp_step.flush()
                os.fsync(fp_step)
                script += "\nexec(open(r'%s').read())\n" % fp_step.name
                fp_step.close()
        else:
            script = scripts[0]

        self.write_and_run_script(environment, script, pipe_output=pipe_output)

    def write_and_run_script(self, environment, script, pipe_output):
        """Use an environment path and a temporary file to store the script
        Args:

            environment:
                The virtual environment used to run the scripts
            script:
                The virtual environment used to run the scripts
            pipe_output:
                Indicates whether to pipe the output of the subprocess or just return it as is.
        """
        if debug_settings():
            fp = open(
                str(self._configuration.tmp_path().joinpath("album_test.py")), "w"
            )
            module_logger().debug(
                "Executable file in: %s..."
                % str(self._configuration.tmp_path().joinpath("album_test.py"))
            )
        else:
            fp = tempfile.NamedTemporaryFile(mode="w+", delete=False)
            module_logger().debug("Executable file in: %s..." % fp.name)
        fp.write(script)
        fp.flush()
        os.fsync(fp)
        fp.close()
        self.run_script(environment.path(), fp.name, pipe_output=pipe_output)
        Path(fp.name).unlink()

    def create_or_update_env(
        self, environment: IEnvironment, album_api_version: str = None
    ):
        """Creates or updates the environment"""
        if self.environment_exists(environment.name()):
            self.update(environment)
        else:
            self.create(environment, album_api_version)

    def update(self, environment: IEnvironment):
        """Updates the environment"""
        module_logger().debug("Skip installing environment %s..." % environment.name())
        pass  # ToDo: implement and change log message

    def create(self, environment: IEnvironment, album_api_version=None):
        """Creates environment a solution runs in."""
        if environment.yaml_file():
            self.create_environment_from_file(
                environment.yaml_file(), environment.name(), album_api_version
            )
        else:
            module_logger().warning(
                "No yaml file specified. Creating Environment without dependencies!"
            )
            self.create_environment(environment.name(), album_api_version)

    def install(self, environment: IEnvironment, album_api_version=None):
        """Creates or updates an an environment and installs album in the target environment."""
        self.create_or_update_env(environment, album_api_version)
        self.set_environment_path(environment)
