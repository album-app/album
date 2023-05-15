from pathlib import Path

from album.core.api.model.configuration import IConfiguration
from album.core.api.model.environment import IEnvironment
from album.core.controller.package_manager import PackageManager
from album.core.utils import subcommand
from album.core.utils.operations.file_operations import force_remove
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class CondaLockManager(PackageManager):
    """Class for creating conda environment from conda lock files. Since a separate executable is used, this
        functionality is separated from the CondaManager class."""

    def __init__(self, configuration: IConfiguration):
        super().__init__(configuration)
        self._conda_lock_executable = self._configuration.conda_lock_executable()

    def create_environment_from_lockfile(self, conda_lock_file: Path, environment_name: str):
        """Create a conda environment from a conda lock file. If the environment already exists,
        it will be removed first."""
        if self.environment_exists(environment_name):
            module_logger().debug("Environment already exists, removing it first...")
            self.remove_environment(environment_name)

        env_prefix = self._environment_name_to_path(environment_name)
        force_remove(env_prefix)  # Force remove is needed since the env location need to be created to create the link to it but for micromamba the env location has to be created by micromamba itself or an error is raised

        if not (str(conda_lock_file).endswith(".yml") or str(conda_lock_file).endswith(".yaml")):
            raise NameError("Conda lock file needs to be a yml or yaml file!")

        install_args = self._get_env_create_args(env_prefix, conda_lock_file)

        try:
            subcommand.run(install_args, log_output=True)
        except RuntimeError as e:
            # cleanup after failed installation
            if self.environment_exists(environment_name):
                module_logger().debug("Cleanup failed environment creation...")
                self.remove_environment(environment_name)
            raise RuntimeError("Command failed due to: %s" % e) from e

    def _get_env_create_args(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess unsing the installed package manager"""
        if self.get_package_manager() == "micromamba":
            return self._get_install_args_micromamba(env_prefix, lock_file)
        elif self.get_package_manager() == "mamba":
            return self._get_install_args_mamba(env_prefix, lock_file)
        else:
            return self._get_install_args_conda(env_prefix, lock_file)

    def _get_install_args_micromamba(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess using the micromamba"""
        return [str(self._conda_lock_executable), "install", "-p", str(env_prefix), "--conda",
                str(self.get_install_environment_executable()), str(lock_file)]

    def _get_install_args_conda(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess using conda"""
        return [str(self._conda_lock_executable), "install", "-p", str(env_prefix), '--no-mamba',
                '--no-micromamba', str(lock_file)]  # , "--conda", self.get_install_environment_executable() this is not pased since the conda executable is mots of the times just the str conda which is not a supported arguement of conda-lock

    def _get_install_args_mamba(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess using mamba"""
        return [str(self._conda_lock_executable), "install", "-p", str(env_prefix), '--no-micromamba',
                "--conda", str(self.get_install_environment_executable()), str(lock_file)]

    def create(self, environment: IEnvironment, album_api_version: str = None, conda_lock_file: Path = None):
        """Creates environment a solution runs in."""
        self.create_environment_from_lockfile(conda_lock_file, environment.name())

    def get_active_environment_name(self):
        raise NotImplementedError("conda-lock does not support getting the active environment name!")

    def get_active_environment_path(self):
        raise NotImplementedError("conda-lock does not support getting the active environment path!")

    def _get_run_script_args(self, environment_path, script_full_path):
        raise NotImplementedError("conda-lock does not support getting the run script args!")

    def _get_remove_env_args(self, path):
        raise NotImplementedError("conda-lock does not support getting the active environment name!")
