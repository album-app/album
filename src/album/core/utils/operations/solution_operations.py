"""Operations for the solution object."""
import copy
import hashlib
import json
from datetime import date, time
from typing import Any, Dict, List, Optional, Union

from album.environments.api.model.environment import IEnvironment
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


def set_environment_paths(solution: ISolution, environment: IEnvironment) -> None:
    """Set the available cache paths of the solution object, given the environment used to run it."""
    solution.installation().set_environment_path(environment.path())


def get_deploy_dict(solution: ISolution) -> Dict[str, Any]:
    """Return a dictionary with the relevant deployment key/values for a given album."""
    d = {}

    for k in solution.setup().keys():
        value = solution.setup()[k]
        if not callable(value) and k != "dependencies":
            # deepcopy necessary. Else original album object will loose "action" attributes in its arguments
            d[k] = copy.deepcopy(value)

    return _remove_action_from_args(d)


def _remove_action_from_args(solution_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Remove action from the args dictionary."""
    if "args" in solution_dict:
        for arg in solution_dict["args"]:
            if isinstance(arg, dict):
                # iterate and remove callable values
                for key in arg.keys():
                    if callable(arg[key]):
                        arg[key] = "%s_function" % key
    return solution_dict


def get_parent_dict(solution: ISolution) -> Optional[dict]:
    """Return the parent dictionary of a solution."""
    if solution.setup().dependencies and "parent" in solution.setup().dependencies:
        return solution.setup().dependencies["parent"]
    return None


def create_hash(string_representation: str) -> str:
    """Create a hash from a string."""
    hash_val = hashlib.md5(string_representation.encode("utf-8")).hexdigest()

    return hash_val


def get_solution_hash(solution_attrs: Dict[str, Any], keys: List[str]):
    """Create a hash from the solution dictionary."""
    return create_hash(
        ":".join([json.dumps(solution_attrs[k]) for k in keys if k in solution_attrs])
    )


def serialize_json(catalogs_as_dict: Dict[str, Any]) -> str:
    """Serialize a dictionary to a json string."""
    return json.dumps(catalogs_as_dict, sort_keys=True, indent=4, default=serialize)


def serialize(obj: Any) -> Union[str, Dict[str, Any]]:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, date):
        serial = obj.isoformat()
        return serial

    if isinstance(obj, time):
        serial = obj.isoformat()
        return serial

    return obj.__dict__
