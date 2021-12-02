from abc import ABCMeta, abstractmethod

from album.api.model.catalog import ICatalog
from album.api.model.environment import IEnvironment
from album.runner.api.model.solution import ISolution


class EnvironmentInterface:
    """Manages everything around the environment a solution lives in."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def install_environment(self, active_solution: ISolution, catalog: ICatalog) -> IEnvironment:
        raise NotImplementedError

    @abstractmethod
    def set_environment(self, active_solution: ISolution, catalog: ICatalog) -> IEnvironment:
        """Resolves the environment the active solution runs in.

        Returns the resolve result of the parent of the active solution.

        """
        raise NotImplementedError

    @abstractmethod
    def remove_environment(self, environment: IEnvironment):
        """Removes an environment."""
        raise NotImplementedError

    @abstractmethod
    def run_scripts(self, environment: IEnvironment, scripts):
        """Runs scripts in an environment"""
        raise NotImplementedError

    @abstractmethod
    def get_conda_manager(self):
        raise NotImplementedError

    @abstractmethod
    def get_environment_base_folder(self):
        """Returns the location all album-created environments live in."""
        raise NotImplementedError
