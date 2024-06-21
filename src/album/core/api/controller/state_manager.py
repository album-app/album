"""Interface for the state manager."""
from abc import ABCMeta, abstractmethod

from album.runner.core.api.model.solution import ISolution


class IStateManager:
    """Interface for the state manager."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def load(self, path) -> ISolution:
        """Load the state from the given path."""
        raise NotImplementedError
