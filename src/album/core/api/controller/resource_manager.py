"""Interface for the resource manager class."""
from abc import ABCMeta, abstractmethod
from pathlib import Path

from album.runner.core.api.model.solution import ISolution

from album.core.api.model.catalog import ICatalog


class IResourceManager:
    """Class handling the build process of solutions, so collecting all deploy important files."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def write_solution_files(
        self,
        catalog: ICatalog,
        catalog_local_src: str,
        active_solution: ISolution,
        deploy_path: Path,
        no_conda_lock: bool,
    ):
        """Write the solution files to the deploy path."""
        raise NotImplementedError

    @abstractmethod
    def write_solution_environment_file(self, solution: ISolution, solution_home: Path):
        """Write the environment file for the solution."""
        raise NotImplementedError
