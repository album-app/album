from pathlib import Path

from album.core.utils import subcommand
from album.core.utils.operations.file_operations import force_remove
from album.runner.album_logging import get_active_logger


class CondaLockManager:
    """Class for creating conda environment from conda lock files. Since a separate executable is used, this
        functionality is separated from the CondaManager class."""

    def __init__(self, conda_lock_executable, package_manager):
        super().__init__(self, )
        self._conda_lock_executable = conda_lock_executable
        self._package_manager = package_manager

    def create_environment_from_lockfile(self, conda_lock_file: Path, environment_path):
        """Create a conda environment from a conda lock file. If the environment already exists,
        it will be removed first."""
        if self._package_manager.environment_exists(environment_path):
            get_active_logger().debug("Environment already exists, removing it first...")
            self._package_manager.remove_environment(environment_path)

        env_prefix = environment_path
        force_remove(env_prefix)  # Force remove is needed since the env location need to be created to create the link to it but for micromamba the env location has to be created by micromamba itself or an error is raised

        if not (str(conda_lock_file).endswith(".yml") or str(conda_lock_file).endswith(".yaml")):
            raise NameError("Conda lock file needs to be a yml or yaml file!")

        install_args = self._get_env_create_args(env_prefix, conda_lock_file)

        try:
            subcommand.run(install_args, log_output=True)
        except RuntimeError as e:
            # cleanup after failed installation
            if self._package_manager.environment_exists(env_prefix):
                get_active_logger().debug("Cleanup failed environment creation...")
                self._package_manager.remove_environment(env_prefix)
            raise RuntimeError("Command failed due to: %s" % e) from e

    def _get_env_create_args(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess unsing the installed package manager"""
        if self._package_manager.get_package_manager() == "micromamba":
            return self._get_install_args_micromamba(env_prefix, lock_file)
        elif self._package_manager.get_package_manager() == "mamba":
            return self._get_install_args_mamba(env_prefix, lock_file)
        else:
            return self._get_install_args_conda(env_prefix, lock_file)

    def _get_install_args_micromamba(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess using the micromamba"""
        return [str(self._conda_lock_executable), "install", "-p", str(env_prefix), "--conda",
                str(self._package_manager.get_install_environment_executable()), str(lock_file)]

    def _get_install_args_conda(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess using conda"""
        return [str(self._conda_lock_executable), "install", "-p", str(env_prefix), '--no-mamba',
                '--no-micromamba', str(lock_file)]  # , "--conda", self.get_install_environment_executable() this is not pased since the conda executable is mots of the times just the str conda which is not a supported arguement of conda-lock

    def _get_install_args_mamba(self, env_prefix: Path, lock_file: Path):
        """Returns the arguments for the conda-lock install subprocess using mamba"""
        return [str(self._conda_lock_executable), "install", "-p", str(env_prefix), '--no-micromamba',
                "--conda", str(self._package_manager.get_install_environment_executable()), str(lock_file)]
