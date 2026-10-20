"""Interface for the resource manager class."""

from abc import ABCMeta, abstractmethod
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
        """Write the environment album installs for the solution to solution_home.

        It is the environment of the solution with album-solution-api added, the one album
        deploy locks, written to solution.environment.yml. A relative path of an environment
        file starts at solution_folder, the folder of the solution.
        """
        raise NotImplementedError

    @abstractmethod
    def check_file_dependencies(
        self,
        solution: ISolution,
        solution_folder: Optional[Path],
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """Check that the environment and the resource file a solution names by its path exist.

        Args:
            solution:
                The solution.
            solution_folder:
                The folder of the solution, where relative paths start. None for a solution
                given as a single file, which cannot name a file by a relative path.
            dependencies:
                The ones to check, environment_file or resource_file; both if None.

        Raises:
            TypeError: if a file does not exist.
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

        The environment file is its content as a string, a url, the path of a .yml file (a
        relative path starts at solution_folder, the folder of the solution), a StringIO or a
        dictionary.

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
