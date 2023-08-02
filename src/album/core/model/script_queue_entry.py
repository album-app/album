from pathlib import Path

from album.environments.api.model.environment import IEnvironment
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution


class ScriptQueueEntry:
    def __init__(
        self,
        coordinates: ICoordinates,
        script_path: Path,
        solution_action: ISolution.Action,
        args,
        environment: IEnvironment,
        solution_installation_path,
        solution_package_path,
    ):
        self.script = script_path
        self.solution_action = solution_action
        self.solution_installation_path = solution_installation_path
        self.solution_package_path = solution_package_path
        self.args = args
        self.environment = environment
        self.coordinates = coordinates
