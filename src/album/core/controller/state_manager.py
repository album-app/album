from typing import List, Optional

from album.runner import api
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.state_manager import IStateManager


class StateManager(IStateManager):
    def __init__(self, album: IAlbumController):
        self._active_solution: List[ISolution] = []
        self.album = album
        # overwrite album setup with this setup
        api.setup = self._setup_solution

    def load(self, path: str) -> ISolution:
        get_active_logger().debug(f"Loading solution from {path}...")
        with open(path) as f:
            solution = f.read()
        exec(solution)
        active_solution = self._get_active_solution()
        if active_solution is None:
            get_active_logger().error("Cannot load solution %s!" % path)
            raise ValueError("Cannot load solution %s!" % path)

        active_solution.set_script(path)
        self._pop_active_solution()
        return active_solution

    def _setup_solution(self, **attrs) -> None:
        attrs = self.album.migration_manager().migrate_solution_attrs(attrs)
        next_solution = Solution(attrs)
        self._push_active_solution(next_solution)

    def _push_active_solution(self, solution_object: ISolution) -> None:
        self._active_solution.insert(0, solution_object)

    def _get_active_solution(self) -> Optional[ISolution]:
        if len(self._active_solution) > 0:
            return self._active_solution[0]
        return None

    def _pop_active_solution(self) -> Optional[ISolution]:
        if len(self._active_solution) > 0:
            return self._active_solution.pop(0)
        else:
            return None
