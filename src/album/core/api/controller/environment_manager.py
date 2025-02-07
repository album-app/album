"""Interface for managing environments."""
from abc import ABCMeta, abstractmethod
from typing import List, Mapping, Optional, Union

from album.environments.api.environment_api import IEnvironmentAPI
from album.environments.api.model.environment import IEnvironment

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.link import Link
from album.runner.core.api.model.coordinates import ICoordinates


class IEnvironmentManager:
    """Manage everything around the environment a solution lives in.

    Uses the environment API to install, remove, and run scripts in environments.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def install_environment(
        self, collection_solution: ICollectionSolution, allow_recursive: bool = False
    ) -> IEnvironment:
        """Install an environment for the given solution."""
        raise NotImplementedError

    @abstractmethod
    def set_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        """Resolve the environment the active solution runs in.

        Returns the resolve result of the parent of the active solution.

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
