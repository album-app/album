import sys
from typing import Optional

from album.core.controller.migration_manager import MigrationManager
from album.runner import album_logging
from album.runner.model.solution import Solution

module_logger = album_logging.get_active_logger

__version__ = "0.1.0"
__author__ = "Kyle Harrington, Jan Philipp Albrecht, Deborah Schmidt"
__email__ = "album@kyleharrington.com"


"""
Global variable for tracking the currently active solution. Do not use this 
directly instead use get_active_solution()
"""
_active_solution = []


def setup_solution(**attrs):
    """This configures a solution for use by the main album tool."""
    global _active_solution

    # FIXME: what if the solution cant be created based on the attrs?
    # suggestion: read out a setup parameter with a version and then decide what to do.
    # also based on the version one could use another scrip-creator

    # todo: MIGRATION MANAGER SHOULD LOAD SOLUTIONS AND FAIL IF VERSION MISSMATCH

    MigrationManager().validate_solution_attrs(attrs)
    next_solution = Solution(attrs)
    push_active_solution(next_solution)


# overwrite album setup with this setup
sys.modules['album.runner'].setup = setup_solution


def push_active_solution(solution_object):
    """Pop a album to the _active_solution stack."""
    global _active_solution
    _active_solution.insert(0, solution_object)


def get_parent_solution() -> Optional[Solution]:
    """Return the parent solution of the currently active solution."""
    global _active_solution
    if len(_active_solution) > 1:
        return _active_solution[1]
    return None


def get_active_solution() -> Optional[Solution]:
    """Return the currently active solution, which is defined globally."""
    global _active_solution
    if len(_active_solution) > 0:
        return _active_solution[0]
    return None


def pop_active_solution():
    """Pop the currently active album from the _active_solution stack."""
    global _active_solution

    if len(_active_solution) > 0:
        return _active_solution.pop(0)
    else:
        return None


def load_and_push_solution(path) -> Optional[Solution]:
    """Load album script"""
    module_logger().debug(f'Loading solution from {path}...')
    with open(path, "r") as f:
        solution_script = f.read()
    exec(solution_script)
    active_solution = get_active_solution()
    active_solution.script = solution_script
    return active_solution


def load(path) -> Optional[Solution]:
    module_logger().debug(f'Loading solution from {path}...')
    with open(path, "r") as f:
        solution = f.read()
    exec(solution)
    active_solution = get_active_solution()
    active_solution.script = solution
    pop_active_solution()
    return active_solution
