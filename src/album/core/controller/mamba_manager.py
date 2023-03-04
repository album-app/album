from album.core.controller.conda_manager import CondaManager


class MambaManager(CondaManager):
    """Class for handling conda environments via mamba."""

    def __init__(self, conda_executable, mamba_executable, base_env_path):
        super().__init__(conda_executable, base_env_path)
        self._mamba_executable = mamba_executable

    def get_install_environment_executable(self):
        return self._mamba_executable
