from typing import Callable, List, Optional

from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.controller.event_manager import IEventManager
from album.core.api.model.event import IEvent


class EventManager(IEventManager):
    """Class for handling events."""

    class EventCallback:
        def __init__(
            self, event_name: str, method: Callable, solution_id: ICoordinates
        ):
            self.event_name = event_name
            self.method = method
            self.solution_id = solution_id

    def __init__(self):
        self.event_callbacks = []

    def add_listener(
        self,
        event_name: str,
        callback_method: Callable,
        coordinates: Optional[ICoordinates] = None,
    ):
        res = self._filter_callbacks(
            event_name, coordinates=coordinates, callback_method=callback_method
        )
        if not res:
            self.event_callbacks.append(
                EventManager.EventCallback(event_name, callback_method, coordinates)
            )

    def remove_listener(
        self,
        event_name: str,
        callback_method: Callable,
        coordinates: Optional[ICoordinates] = None,
    ) -> None:
        res = self._filter_callbacks(
            event_name, callback_method=callback_method, coordinates=coordinates
        )
        for c in res:
            self.event_callbacks.remove(c)

    def _filter_callbacks(
        self,
        event_name: str,
        coordinates: Optional[ICoordinates] = None,
        callback_method: Optional[Callable] = None,
    ) -> List[EventCallback]:
        if coordinates and callback_method:
            return [
                callback
                for callback in self.event_callbacks
                if callback.event_name == event_name
                and callback.method == callback_method
                and (not callback.solution_id or callback.solution_id == coordinates)
            ]
        if coordinates:
            return [
                callback
                for callback in self.event_callbacks
                if callback.event_name == event_name
                and (not callback.solution_id or callback.solution_id == coordinates)
            ]
        if callback_method:
            return [
                callback
                for callback in self.event_callbacks
                if callback.event_name == event_name
                and callback.method == callback_method
            ]
        return [
            callback
            for callback in self.event_callbacks
            if callback.event_name == event_name
        ]

    def publish(
        self, event: IEvent, coordinates: Optional[ICoordinates] = None
    ) -> None:
        for callback in self._filter_callbacks(event.name(), coordinates=coordinates):
            callback.method(event)
