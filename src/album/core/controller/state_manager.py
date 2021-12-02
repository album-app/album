from typing import Optional

from album.api.album_interface import AlbumInterface
from album.api.controller.state_interface import StateInterface
from album.runner.album_logging import get_active_logger
from album.runner.api import runner
from album.runner.api.model.solution import ISolution
from album.runner.model.solution import Solution


class StateManager(StateInterface):

    def __init__(self, album: AlbumInterface):
        self._active_solution = []
        self.album = album
        # overwrite album setup with this setup
        runner.setup = self._setup_solution

    def _setup_solution(self, **attrs):
        """This configures a solution for use by the main album tool."""

        # FIXME: what if the solution cant be created based on the attrs?
        # suggestion: read out a setup parameter with a version and then decide what to do.
        # also based on the version one could use another scrip-creator

        # todo: MIGRATION MANAGER SHOULD LOAD SOLUTIONS AND FAIL IF VERSION MISSMATCH

        self.album.migration_manager().validate_solution_attrs(attrs)
        next_solution = Solution(attrs)
        self.push_active_solution(next_solution)

    def push_active_solution(self, solution_object: ISolution):
        """Pop a album to the _active_solution stack."""
        self._active_solution.insert(0, solution_object)

    def get_parent_solution(self) -> Optional[ISolution]:
        """Return the parent solution of the currently active solution."""
        if len(self._active_solution) > 1:
            return self._active_solution[1]
        return None

    def get_active_solution(self) -> Optional[ISolution]:
        """Return the currently active solution, which is defined globally."""
        if len(self._active_solution) > 0:
            return self._active_solution[0]
        return None

    def pop_active_solution(self):
        """Pop the currently active album from the _active_solution stack."""
        if len(self._active_solution) > 0:
            return self._active_solution.pop(0)
        else:
            return None

    def load(self, path) -> Optional[ISolution]:
        get_active_logger().debug(f'Loading solution from {path}...')
        with open(path, "r") as f:
            solution = f.read()
        exec(solution)
        active_solution = self.get_active_solution()
        active_solution.set_script(solution)
        self.pop_active_solution()
        return active_solution
