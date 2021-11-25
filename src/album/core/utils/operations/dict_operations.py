from typing import List


def get_dict_entries_from_path(obj, path: str) -> List:
    parts = path.split('.')
    return _get_entries(obj, parts)


def _get_entries(obj, path: List) -> List:
    if len(path) == 0:
        if isinstance(obj, list):
            return obj
        else:
            return [obj]
    current_path = path[0]
    if isinstance(obj, list):
        res = []
        for el in obj:
            res.extend(_get_entries(el, path))
        return res
    if isinstance(obj, dict):
        if current_path in obj:
            path = path.copy()
            path.pop(0)
            return _get_entries(obj[current_path], path)
        else:
            return []