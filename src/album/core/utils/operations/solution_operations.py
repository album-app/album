import copy
import hashlib
import json
from datetime import date, time
from typing import Optional

from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.environment import IEnvironment
from album.core.utils.operations.file_operations import remove_link
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


def set_environment_paths(solution: ISolution, environment: IEnvironment):
    """Sets the available cache paths of the solution object, given the environment used to run it."""
    solution.installation().set_environment_path(environment.path())
    solution.installation().set_environment_name(environment.name())


def get_deploy_dict(solution: ISolution) -> dict:
    """Return a dictionary with the relevant deployment key/values for a given album."""
    d = {}

    for k in solution.setup().keys():
        value = solution.setup()[k]
        if not callable(value) and k != "dependencies":
            # deepcopy necessary. Else original album object will loose "action" attributes in its arguments
            d[k] = copy.deepcopy(value)

    return _remove_action_from_args(d)


def _remove_action_from_args(solution_dict):
    if "args" in solution_dict:
        for arg in solution_dict["args"]:
            if isinstance(arg, dict):
                # iterate and remove callable values
                for key in arg.keys():
                    if callable(arg[key]):
                        arg[key] = "%s_function" % key
    return solution_dict


def get_parent_dict(solution: ISolution) -> Optional[dict]:
    if solution.setup().dependencies and "parent" in solution.setup().dependencies:
        return solution.setup().dependencies["parent"]
    return None


def get_steps_dict(solution: ISolution) -> Optional[dict]:
    return solution.setup().steps


def create_hash(string_representation):
    hash_val = hashlib.md5(string_representation.encode("utf-8")).hexdigest()

    return hash_val


def get_solution_hash(solution_attrs, keys):
    return create_hash(
        ":".join([json.dumps(solution_attrs[k]) for k in keys if k in solution_attrs])
    )


def serialize_json(catalogs_as_dict):
    return json.dumps(catalogs_as_dict, sort_keys=True, indent=4, default=serialize)


def serialize(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, date):
        serial = obj.isoformat()
        return serial

    if isinstance(obj, time):
        serial = obj.isoformat()
        return serial

    return obj.__dict__
