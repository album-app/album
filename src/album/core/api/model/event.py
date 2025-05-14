"""This module contains the interface for an event."""
from abc import ABCMeta, abstractmethod


class IEvent:
    """Interface for an event."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def name(self):
        """Get the name of the event."""
        raise NotImplementedError
