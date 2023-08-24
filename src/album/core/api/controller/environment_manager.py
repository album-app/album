from abc import ABCMeta, abstractmethod

from album.core.api.model.collection_solution import ICollectionSolution
from album.environments.api.controller.environment_handler import IEnvironmentHandler
from album.environments.api.model.environment import IEnvironment


class IEnvironmentManager:
    """Manages everything around the environment a solution lives in."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def install_environment(
        self, collection_solution: ICollectionSolution
    ) -> IEnvironment:
        raise NotImplementedError

    @abstractmethod
    def set_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        """Resolves the environment the active solution runs in.

        Returns the resolve result of the parent of the active solution.

        """
        raise NotImplementedError

    @abstractmethod
    def remove_environment(self, environment: IEnvironment):
        """Removes an environment."""
        raise NotImplementedError

    @abstractmethod
    def run_script(
        self,
        environment: IEnvironment,
        script,
        environment_variables=None,
        argv=None,
        pipe_output=True,
    ):
        """Runs the solution in the target environment

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
    def get_environment_handler(self) -> IEnvironmentHandler:
        raise NotImplementedError

    def get_environment_path(self, environment_name: str, create: bool):
        raise NotImplementedError
