"""Interface for managing environments."""

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.link import Link
from album.environments.api.environment_api import IEnvironmentAPI
from album.environments.api.model.environment import IEnvironment
from album.runner.core.api.model.coordinates import ICoordinates


class IEnvironmentManager:
    """Manage everything around the environment a solution lives in.

    Uses the environment API to install, remove, and run scripts in environments.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def install_environment(
        self,
        collection_solution: ICollectionSolution,
        allow_recursive: bool = False,
        no_conda_lock: bool = False,
    ) -> IEnvironment:
        """Install an environment for the given solution.

        It is installed from the lock file of the solution, if it has one. With
        no_conda_lock, it is solved instead.
        """
        raise NotImplementedError

    @abstractmethod
    def check_lock_file(
        self,
        coordinates: ICoordinates,
        solution_folder: Optional[Path],
        no_conda_lock: bool = False,
    ) -> None:
        """Check that the environment of a solution can be installed from its lock file.

        Raises a RuntimeError if the solution in solution_folder has a lock file, but
        conda-lock, which installs it, is not found, unless no_conda_lock is given: then
        the environment is solved instead.
        """
        raise NotImplementedError

    @abstractmethod
    def check_album_version(self, collection_solution: ICollectionSolution) -> None:
        """Check that the environment of a solution installs no other album version.

        Raises a ValueError naming the album versions its environment installs, other than
        the running one, which installing it only accepts with allow_recursive. The same or
        an unversioned album is accepted. The environment is read as installing the
        solution reads it.
        """
        raise NotImplementedError

    @abstractmethod
    def set_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        """Resolve the environment the solution runs in and set its path on the solution.

        A solution without a parent runs in its own environment. A solution with a
        parent runs in the environment of the solution at the top of its parent chain:
        a parent can have a parent itself, and only the top one has an environment.

        Returns the environment.

        """
        raise NotImplementedError

    @abstractmethod
    def remove_environment(self, environment: IEnvironment) -> bool:
        """Remove an environment."""
        raise NotImplementedError

    @abstractmethod
    def run_script(
        self,
        environment: IEnvironment,
        script: str,
        environment_variables: Optional[
            Union[
                Mapping,
                None,
            ]
        ] = None,
        argv: Optional[List[str]] = None,
        pipe_output: bool = True,
    ) -> None:
        """Run the solution in the target environment.

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
        raise NotImplementedError

    @abstractmethod
    def get_environment_handler(self) -> IEnvironmentAPI:
        """Get the environment handler."""
        raise NotImplementedError

    @abstractmethod
    def get_environment_path(
        self, environment_name: str, create: bool
    ) -> Optional[Link]:
        """Get the path of an environment."""
        raise NotImplementedError

    @abstractmethod
    def get_environment_name(self, coordinates: ICoordinates, catalog: ICatalog) -> str:
        """Get the name of an environment."""
        raise NotImplementedError

    @abstractmethod
    def _append_framework_to_dependencies(
        self,
        content: Dict[str, Any],
        album_api_version: Optional[str],
        runner_package_name: str,
    ) -> Dict[str, Any]:
        """Append the album framework to the environment dependencies."""
        raise NotImplementedError
