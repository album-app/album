import copy
from pathlib import Path
from typing import Optional

from album.core.model.configuration import Configuration
from album.core.model.environment import Environment
from album.runner import album_logging
from album.runner.model.solution import Solution

module_logger = album_logging.get_active_logger


def get_deploy_keys():
    return [
        'group', 'name', 'description', 'version', 'album_api_version',
        'album_version', 'license', 'acknowledgement', 'authors', 'cite', 'tags', 'documentation',
        'covers', 'args', 'title', 'timestamp'
    ]


def set_cache_paths(solution: Solution, catalog):
    """Sets the available cache paths of the solution object, given its catalog_name (where it lives)."""

    # Note: cache paths need the catalog the solution lives in - otherwise there might be problems with solutions
    # of different catalogs doing similar operations (e.g. downloads) as they might share the same cache path.
    path_suffix = Path("").joinpath(solution.coordinates.group, solution.coordinates.name, solution.coordinates.version)
    solution.installation.data_path = Configuration().cache_path_download.joinpath(str(catalog.name), path_suffix)
    solution.installation.app_path = Configuration().cache_path_app.joinpath(str(catalog.name), path_suffix)
    solution.installation.package_path = catalog.get_solution_path(solution.coordinates)
    solution.installation.internal_cache_path = Configuration().cache_path_tmp_internal.joinpath(str(catalog.name), path_suffix)
    solution.installation.user_cache_path = Configuration().cache_path_tmp_user.joinpath(str(catalog.name), path_suffix)


def set_environment_paths(solution: Solution, environment: Environment):
    """Sets the available cache paths of the solution object, given the environment used to run it."""
    solution.installation.environment_path = environment.path
    solution.installation.environment_name = environment.name


def get_deploy_dict(solution: Solution):
    """Return a dictionary with the relevant deployment key/values for a given album."""
    d = {}

    for k in get_deploy_keys():
        # deepcopy necessary. Else original album object will loose "action" attributes in its arguments
        d[k] = copy.deepcopy(solution.setup[k])

    return _remove_action_from_args(d)


def _remove_action_from_args(solution_dict):
    for arg in solution_dict["args"]:
        if isinstance(arg, dict):
            # iterate and remove callable values
            for key in arg.keys():
                if callable(arg[key]):
                    arg[key] = "%s_function" % key
    return solution_dict


def get_parent_dict(solution: Solution) -> Optional[dict]:
    if solution.setup.dependencies and 'parent' in solution.setup.dependencies:
        return solution.setup.dependencies['parent']
    return None


def get_steps_dict(solution) -> Optional[dict]:
    return solution.setup.steps
