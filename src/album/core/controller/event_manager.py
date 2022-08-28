from album.core.api.controller.event_manager import IEventManager
from album.core.api.model.event import IEvent
from album.runner.core.api.model.coordinates import ICoordinates


class EventManager(IEventManager):
    """Class for handling events."""

    class EventCallback:
        def __init__(self, event_name, method, solution_id):
            self.event_name = event_name
            self.method = method
            self.solution_id = solution_id

    def __init__(self):
        self.event_callbacks = []

    def add_listener(
        self, event_name, callback_method, coordinates: ICoordinates = None
    ):
        res = self._filter_callbacks(
            event_name, coordinates=coordinates, callback_method=callback_method
        )
        if not res:
            self.event_callbacks.append(
                EventManager.EventCallback(event_name, callback_method, coordinates)
            )

    def remove_listener(
        self, event_name, callback_method, coordinates: ICoordinates = None
    ):
        res = self._filter_callbacks(
            event_name, callback_method=callback_method, coordinates=coordinates
        )
        for c in res:
            self.event_callbacks.remove(c)

    def _filter_callbacks(
        self, event_name, coordinates: ICoordinates = None, callback_method=None
    ):
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

    def publish(self, event: IEvent, coordinates: ICoordinates = None):
        for callback in self._filter_callbacks(event.name(), coordinates=coordinates):
            callback.method(event)
