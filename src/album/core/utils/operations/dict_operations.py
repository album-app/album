import json
from typing import List


def get_dict_entries_from_attribute_path(obj, attribute_path: str) -> List:
    """"""
    parts = attribute_path.split(".")
    return _get_entries(obj, parts)


def str_to_dict(s):
    return json.loads(s)


def _get_entries(obj, attribute_paths: List) -> List:
    # case single attribute path
    if len(attribute_paths) == 0:
        if isinstance(obj, list):
            return obj
        else:
            return [obj]

    # extract first attribute
    current_path = attribute_paths[0]

    # if given object is a list itself: recursive call for each list entry
    if isinstance(obj, list):
        res = []
        for el in obj:
            res.extend(_get_entries(el, attribute_paths))
        return res

    # recursive iteration through dict-structure to get attribute
    if isinstance(obj, dict):
        if current_path in obj:
            # remove key
            attribute_paths = attribute_paths.copy()
            # remove current_path from attribute_paths (it will be used as dict-identifier)
            attribute_paths.pop(0)
            return _get_entries(obj[current_path], attribute_paths)
        else:
            return []
