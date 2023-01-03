from abc import ABCMeta, abstractmethod

from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.environment import IEnvironment


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
    def run_scripts(self, environment: IEnvironment, scripts, pipe_output=True):
        """Runs the solution in the target environment

        Args:
            scripts:
                List of he scripts calling the solution(s)
            environment:
                The virtual environment used to run the scripts
            pipe_output:
                Indicates whether to pipe the output of the subprocess or just return it as is.
        """
        raise NotImplementedError

    @abstractmethod
    def get_package_manager(self):
        raise NotImplementedError
