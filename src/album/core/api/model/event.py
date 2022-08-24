from abc import ABCMeta, abstractmethod


class IEvent:
    """Interface for an event."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def name(self):
        raise NotImplementedError
