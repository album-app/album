import threading
from typing import List, Optional

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.state_manager import IStateManager
from album.runner import api
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution


class StateManager(IStateManager):
    # A solution file calls album.runner.api.setup, a single function for the whole
    # process, and the solution it creates is taken from the active solutions afterwards.
    # Solutions are therefore loaded one at a time, by all album instances and threads.
    # Re-entrant, as a solution file might load another solution.
    _load_lock = threading.RLock()

    def __init__(self, album: IAlbumController):
        self._active_solution: List[ISolution] = []
        self.album = album
        # overwrite album setup with this setup
        api.setup = self._setup_solution

    def load(self, path: str) -> ISolution:
        get_active_logger().debug(f"Loading solution from {path}...")
        with open(path, encoding="utf-8") as f:
            solution = f.read()
        with StateManager._load_lock:
            # the setup of this album instance, another one might have overwritten it
            previous_setup = api.setup
            api.setup = self._setup_solution
            try:
                exec(solution)
            finally:
                api.setup = previous_setup
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
