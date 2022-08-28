from album.core.api.model.event import IEvent


class Event(IEvent):
    def __init__(self, name):
        self._name = name

    def name(self):
        return self._name
