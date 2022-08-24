from album.core.api.model.configuration import IConfiguration
from album.core.controller.conda_manager import CondaManager


class MambaManager(CondaManager):
    """Class for handling conda environments via mamba."""

    def __init__(self, configuration: IConfiguration):
        super().__init__(configuration)
        self._mamba_executable = self._configuration.mamba_executable()

    def _get_install_environment_executable(self):
        return self._mamba_executable
