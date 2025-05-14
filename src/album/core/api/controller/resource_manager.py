"""Interface for the resource manager class."""
from abc import ABCMeta, abstractmethod
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Union

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

    @abstractmethod
    def handle_env_file_dependency(
        self, env_file: Union[str, Dict[str, Any], StringIO], yml_path: Path
    ):
        """Handle the environment file dependency."""
        raise NotImplementedError
