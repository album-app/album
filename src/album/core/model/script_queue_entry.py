from album.core.api.model.environment import IEnvironment
from album.runner.core.api.model.coordinates import ICoordinates


class ScriptQueueEntry:
    def __init__(self, coordinates: ICoordinates, scripts, environment: IEnvironment):
        self.scripts = scripts
        self.environment = environment
        self.coordinates = coordinates
