from abc import ABCMeta, abstractmethod

from album.core.model.catalog import Catalog
from album.core.model.environment import Environment
from album.runner.model.solution import Solution


class EnvironmentInterface:
    """Manages everything around the environment a solution lives in."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def install_environment(self, active_solution: Solution, catalog: Catalog) -> Environment:
        raise NotImplementedError

    @abstractmethod
    def set_environment(self, active_solution: Solution, catalog: Catalog) -> Environment:
        """Resolves the environment the active solution runs in.

        Returns the resolve result of the parent of the active solution.

        """
        raise NotImplementedError

    @abstractmethod
    def remove_environment(self, environment: Environment):
        """Removes an environment."""
        raise NotImplementedError

    @abstractmethod
    def run_scripts(self, environment: Environment, scripts):
        """Runs scripts in an environment"""
        raise NotImplementedError

    @abstractmethod
    def get_conda_manager(self):
        raise NotImplementedError

    @abstractmethod
    def get_environment_base_folder(self):
        """Returns the location all album-created environments live in."""
        raise NotImplementedError
