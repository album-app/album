from album.core.controller.conda_manager import CondaManager


class MambaManager(CondaManager):
    """Class for handling conda environments via mamba."""

    def __init__(self, mamba_executable):
        super().__init__(mamba_executable, "mamba")

