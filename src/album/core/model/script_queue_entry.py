from album.core.model.environment import Environment

from album.runner.model.coordinates import Coordinates


class ScriptQueueEntry:
    def __init__(self, coordinates: Coordinates, scripts, environment: Environment):
        self.scripts = scripts
        self.environment = environment
        self.coordinates = coordinates
