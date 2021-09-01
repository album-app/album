import sys
from typing import Optional

from album.core.model.album_base import AlbumClass
from album_runner import logging

module_logger = logging.get_active_logger

"""
Global variable for tracking the currently active solution. Do not use this 
directly instead use get_active_solution()
"""
global _active_solution
_active_solution = []


def setup_solution(**attrs):
    """This configures a solution for use by the main album tool."""
    global _active_solution
    next_solution = AlbumClass(attrs)
    push_active_solution(next_solution)


# overwrite album_runner setup with this setup
sys.modules['album_runner'].setup = setup_solution


def push_active_solution(solution_object):
    """Pop a album to the _active_solution stack."""
    global _active_solution
    _active_solution.insert(0, solution_object)


def get_parent_solution() -> Optional[AlbumClass]:
    """Return the parent solution of the currently active solution."""
    global _active_solution
    if len(_active_solution) > 1:
        return _active_solution[1]
    return None


def get_active_solution() -> Optional[AlbumClass]:
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


def load_and_push_solution(path) -> Optional[AlbumClass]:
    """Load album script"""
    module_logger().debug(f'Loading solution from {path}...')
    with open(path, "r") as f:
        solution_script = f.read()
    exec(solution_script)
    active_solution = get_active_solution()
    active_solution.script = solution_script
    return active_solution


def load(path) -> Optional[AlbumClass]:
    module_logger().debug(f'Loading solution from {path}...')
    with open(path, "r") as f:
        solution = f.read()
    exec(solution)
    active_solution = get_active_solution()
    active_solution.script = solution
    pop_active_solution()
    return active_solution
