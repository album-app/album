"""Operations for the solution object."""

import copy
import hashlib
import json
from datetime import date, time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from packaging.version import InvalidVersion, Version

from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.environments.api.model.environment import IEnvironment
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger

# The files album deploy writes next to the solution file. A copy of them in the folder of a
# solution, e.g. of one cloned from a catalog, belongs to another deployment.
FILES_WRITTEN_BY_DEPLOY = [
    DefaultValues.solution_yml_default_name.value,
    DefaultValues.solution_environment_default_name.value,
    DefaultValues.solution_conda_lock_default_name.value,
    DefaultValues.solution_resources_default_name.value,
]

# The copy album deploy writes of the file a solution names in its dependencies. A deployed
# solution is installed from the copy, not from the file.
DEPLOYED_COPIES = {
    "environment_file": DefaultValues.solution_environment_default_name.value,
    "resource_file": DefaultValues.solution_resources_default_name.value,
}


def get_solution_folder(collection_solution: ICollectionSolution) -> Optional[Path]:
    """Return the folder a solution is installed from, where its relative paths start.

    Once that folder is gone, as a download album removed after copying it, album's copy of
    it. None for a solution installed from a single file, which has no folder.
    """
    if collection_solution.is_single_file():
        return None
    path = collection_solution.path()
    if path is not None and Path(path).parent.is_dir():
        return Path(path).parent
    return collection_solution.loaded_solution().installation().package_path()


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


def version_sort_key(version: str) -> Tuple[int, Union[Version, str]]:
    """Sort key ordering PEP 440 versions numerically, others (e.g. 0.1.0-SNAPSHOT) by string.

    Parsable versions rank above unparsable ones, so the second tuple element is
    only ever compared between values of the same type.
    """
    try:
        return 1, Version(version)
    except InvalidVersion:
        return 0, version


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
