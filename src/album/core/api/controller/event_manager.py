from abc import ABCMeta, abstractmethod

from album.core.api.model.event import IEvent
from album.runner.core.api.model.coordinates import ICoordinates


class IEventManager:
    """Interface handling events."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def add_listener(self, event_name, callback, coordinates: ICoordinates = None):
        """Add callback method for specific event"""
        raise NotImplementedError

    @abstractmethod
    def remove_listener(self, event_name, callback, coordinates: ICoordinates = None):
        """Add callback method for specific event"""
        raise NotImplementedError

    def publish(self, event: IEvent, coordinates: ICoordinates = None):
        """Publish an event to anyone listening to events with the same name"""
        raise NotImplementedError
