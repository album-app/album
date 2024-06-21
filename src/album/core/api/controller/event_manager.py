"""Interface handling events."""
from abc import ABCMeta, abstractmethod
from typing import Callable, Optional

from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.model.event import IEvent


class IEventManager:
    """Interface handling events."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def add_listener(
        self,
        event_name: str,
        callback_method: Callable,
        coordinates: Optional[ICoordinates] = None,
    ) -> None:
        """Add callback method for specific event."""
        raise NotImplementedError

    @abstractmethod
    def remove_listener(
        self,
        event_name: str,
        callback_method: Callable,
        coordinates: Optional[ICoordinates] = None,
    ) -> None:
        """Add callback method for specific event."""
        raise NotImplementedError

    def publish(
        self, event: IEvent, coordinates: Optional[ICoordinates] = None
    ) -> None:
        """Publish an event to anyone listening to events with the same name."""
        raise NotImplementedError
