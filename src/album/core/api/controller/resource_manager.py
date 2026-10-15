"""Interface for the resource manager class."""

from abc import ABCMeta, abstractmethod
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional, Union

from album.core.api.model.catalog import ICatalog
from album.runner.core.api.model.solution import ISolution


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
    def write_solution_environment_file(
        self,
        solution: ISolution,
        solution_home: Path,
        solution_folder: Optional[Path] = None,
    ):
        """Write the environment file for the solution to solution_home.

        An environment file given as a path is taken from solution_folder, the folder of the solution.
        """
        raise NotImplementedError

    @abstractmethod
    def check_files_in_solution_folder(
        self, solution: ISolution, solution_folder: Optional[Path]
    ) -> None:
        """Check that the environment and the resource file of a solution are in its folder.

        Only files given as a path are checked: they are installed and deployed with the folder
        of the solution, so they have to be inside it and must not be hidden.

        Args:
            solution: The solution.
            solution_folder: The folder of the solution, None for a solution that is a single file.

        Raises:
            TypeError: if a file is not in the folder of the solution.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_env_file_dependency(
        self,
        env_file: Union[str, Dict[str, Any], StringIO],
        yml_path: Path,
        solution_folder: Optional[Path] = None,
    ):
        """Write the environment file of a solution to yml_path.

        The environment file is its content as a string, a url, the path of a .yml file in
        solution_folder, the folder of the solution, relative to it, a StringIO or a dictionary.

        Raises:
            TypeError: if the environment file has none of these forms.
        """
        raise NotImplementedError

    @abstractmethod
    def handle_resource_file_dependency(
        self,
        resource_file: Union[str, Dict[str, Any], StringIO],
        yml_path: Path,
        solution_folder: Optional[Path] = None,
    ):
        """Write the resource file of a solution to yml_path. It takes the same forms as the environment file."""
        raise NotImplementedError
