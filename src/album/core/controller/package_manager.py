import json
import os
import tempfile
from abc import ABCMeta, abstractmethod
from pathlib import Path

import yaml
from packaging import version

from album.core.api.model.environment import IEnvironment
from album.core.model.default_values import DefaultValues
from album.core.utils import subcommand
from album.core.utils.operations.file_operations import (
    remove_link, force_remove,
)
from album.core.utils.subcommand import SubProcessError
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class PackageManager:
    """Parent class for all package managers, like Conda, Mamba, Micromamba, etc."""

    __metaclass__ = ABCMeta

    def __init__(self, install_executable, package_manager):
        self._install_env_executable = install_executable
        self._package_manager = package_manager

    def get_install_environment_executable(self):
        return self._install_env_executable

    def get_package_manager(self):
        return self._package_manager

    @abstractmethod
    def get_active_environment_name(self):
        """Returns the environment from the active album. Implemented in Child classes"""
        raise NotImplementedError

    @abstractmethod
    def get_active_environment_path(self):
        """Returns the environment for the active album. Implemented in Child classes"""
        raise NotImplementedError

    @abstractmethod
    def _get_env_create_args(self, env_file, env_prefix):
        """Returns the arguments for the environment creation command. Implemented in Child classes"""
        raise NotImplementedError

    @abstractmethod
    def _get_run_script_args(self, environment_path, script_full_path):
        """Returns the arguments for a conda run in solution env call. Implemented in Child classes"""
        raise NotImplementedError

    @abstractmethod
    def _get_remove_env_args(self, path):
        """Returns the arguments for the environment removal command. Implemented in Child classes"""
        raise NotImplementedError

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
        """Returns a list of all subdirectories of a given directory."""
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

    def environment_exists(self, environment_path):
        """Checks whether an environment already exists or not.

        Args:
            environment_path:
                The path of an environment.

        Returns:
            True when environment exists else false.
        """
        environment_list = self.get_environment_list()

        return (
            True
            if (
                environment_path
                and environment_path.resolve() in environment_list
                and os.listdir(environment_path)
            )
            else False
        )

    def remove_environment(self, environment_path) -> bool:
        """Removes an environment given its path. Does nothing when environment does not exist.

        Args:
            environment_path:
                The path of the environment to remove

        Returns:
            True, when removal succeeded, else False

        """
        if self.get_active_environment_path() == environment_path:
            module_logger().warning("Cannot remove active environment! Skipping...")
            return False

        if not self.environment_exists(environment_path):
            module_logger().warning("Environment does not exist! Skipping...")
            return False

        try:
            subprocess_args = self._get_remove_env_args(environment_path)
            subcommand.run(subprocess_args, log_output=False)
        except SubProcessError:
            module_logger().debug(
                "Can't delete environment via command line call, deleting the folder next..."
            )
        # try to remove file content if any but don't fail:
        remove_link(environment_path)
        return True

    def get_info(self):
        """Get the info of the conda installation on the corresponding system.

        Returns:
            dictionary corresponding to conda info.
        """
        subprocess_args = [self.get_install_environment_executable(), "info", "--json"]
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
            self.get_install_environment_executable(),
            "list",
            "--json",
            "--prefix",
            str(environment_path),
        ]
        output = subcommand.check_output(subprocess_args)
        return json.loads(output)

    def create_environment_from_file(
            self, yaml_path, environment_path, album_api_version=None
    ):
        """Creates a conda environment given a path to a yaml file and its path.

        Args:
            yaml_path:
                The path to the file.
            environment_path:
                The path of the environment.
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
        if self.environment_exists(environment_path):
            self.remove_environment(environment_path)

        if not (str(yaml_path).endswith(".yml") or str(yaml_path).endswith(".yaml")):
            raise NameError("File needs to be a yml or yaml file!")

        yaml_path = Path(yaml_path)

        if not (yaml_path.is_file() and yaml_path.stat().st_size > 0):
            raise ValueError("File not a valid yml file!")

        with open(yaml_path, "r") as f:
            content = yaml.safe_load(f)

        self._append_runner_and_install(album_api_version, environment_path, content)

    @staticmethod
    def append_framework_to_yml(content, album_api_version):
        """Appends the album runner to the yml file."""
        if version.parse(album_api_version) >= version.parse(
                DefaultValues.first_runner_conda_version.value
        ):
            return PackageManager._append_framework_via_conda_to_yml(
                content, album_api_version
            )
        else:
            return PackageManager._append_framework_via_pip_to_yml(
                content, album_api_version
            )

    @staticmethod
    def _append_framework_via_conda_to_yml(content, album_api_version):
        """Appends the album runner as conda dependency to the yml file."""
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
        """Appends the album runner as pip dependency to the yml file."""
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

    def create_environment(self, environment_path, album_api_version=None, force=False):
        """Creates a conda environment with python (latest version) installed.

        Args:
            environment_path:
                The desired environment path.
            force:
                If True, force creates the environment by deleting the old one.
            album_api_version:
                The api version (runner version) in the environment.

        Raises:
            RuntimeError:
                When the environment could not be created due to whatever reasons.

        """
        env_exists = self.environment_exists(environment_path)
        if force and env_exists:
            self.remove_environment(environment_path)
        else:
            if env_exists:
                raise EnvironmentError(
                    "Environment with name %s already exists!" % environment_path
                )

        self._append_runner_and_install(
            album_api_version, environment_path, DefaultValues.default_solution_env_content.value
        )

    def _append_runner_and_install(self, album_api_version, environment_path, environment_content):
        """Appends the album runner to the yml file and installs the solution environment."""
        if not album_api_version:
            album_api_version = DefaultValues.runner_api_packet_version.value

        environment_content = self.append_framework_to_yml(
            environment_content, album_api_version
        )
        env_prefix = os.path.normpath(environment_path)
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
            if self.environment_exists(environment_path):
                module_logger().debug("Cleanup failed environment creation...")
                self.remove_environment(environment_path)
            raise RuntimeError("Command failed due to reasons above!") from e
        finally:
            os.remove(env_file.name)

    def run_script(
        self,
        environment: IEnvironment,
        script,
        environment_variables=None,
        argv=None,
        pipe_output=True,
    ):
        """Runs the solution in the target environment

        Args:
            script:
                Script calling the solution
            environment:
                The virtual environment used to run the script
            environment_variables:
                The environment variables to attach to the script process
            argv:
                The arguments to attach to the script process
            pipe_output:
                Indicates whether to pipe the output of the subprocess or just return it as is.
        """
        if not environment.path():
            raise EnvironmentError(
                "Could not find environment %s. Is the solution installed?"
                % environment.name()
            )

        module_logger().debug("run_in_environment: %s..." % str(environment.path()))

        subprocess_args = self._get_run_script_args(environment.path(), script)
        if argv and len(argv) > 1:
            subprocess_args.extend(argv[1:])
        subcommand.run(
            subprocess_args, pipe_output=pipe_output, env=environment_variables
        )

    def is_installed(self, environment_path: str, package_name, min_package_version=None):
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

    def create_or_update_env(self, environment: IEnvironment, album_api_version: str = None,
                             conda_lock_file: Path = None):
        """Creates or updates the environment"""
        if self.environment_exists(environment.name()):
            self.update(environment)
        else:
            self.create(environment, album_api_version, conda_lock_file)

    def update(self, environment: IEnvironment):
        """Updates the environment"""
        module_logger().debug("Skip installing environment %s..." % environment.name())
        pass  # ToDo: implement and change log message

    def create(self, environment: IEnvironment, album_api_version: str = None, conda_lock_file: Path = None):
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

    def install(self, environment: IEnvironment, album_api_version: str = None, conda_lock_file=None):
        """Creates or updates an an environment."""
        self.create_or_update_env(environment, album_api_version, conda_lock_file)
