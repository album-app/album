import copy
from pathlib import Path

from album.core.model.configuration import Configuration
from album.core.model.environment import Environment
from album_runner import AlbumRunner
from album_runner import logging

module_logger = logging.get_active_logger


class Solution(AlbumRunner):
    """Extension of a album-runner album class."""

    # CAUTION: deploy_keys also used for resolving. Make sure keys do not contain callable values.
    # If they do, add "to_string" method for @get_deploy_dict. Example see @_remove_action_from_args.
    deploy_keys = [
        'group', 'name', 'description', 'version', 'format_version', 'tested_album_version',
        'min_album_version', 'license', 'git_repo', 'authors', 'cite', 'tags', 'documentation',
        'covers', 'args', 'title', 'timestamp'
    ]

    def get_deploy_dict(self):
        """Return a dictionary with the relevant deployment key/values for a given album."""
        d = {}

        for k in Solution.deploy_keys:
            # deepcopy necessary. Else original album object will loose "action" attributes in its arguments
            d[k] = copy.deepcopy(self.__dict__[k])

        return self._remove_action_from_args(d)

    @staticmethod
    def _remove_action_from_args(solution_dict):
        for arg in solution_dict["args"]:
            if isinstance(arg, dict):
                # iterate and remove callable values
                for key in arg.keys():
                    if callable(arg[key]):
                        arg[key] = "%s_function" % key
        return solution_dict

    # Note: setup- and API-keywords in the album_runner

    def __init__(self, attrs=None):
        """Sets object attributes in setup_keywords.

        Args:
            attrs:
                Dictionary containing the attributes.
        """
        # Attributes from the solution.py
        super().__init__(attrs)

        self.environment = None
        self.cache_path_download = None
        self.cache_path_app = None
        self.cache_path_solution = None

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get_arg(self, k):
        """Get a specific named argument for this album if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]

    def set_environment(self, catalog_name):
        """Initializes the Environment of the solution. This is not an installation!"""
        environment_name = self.get_environment_name(catalog_name)
        self.set_cache_paths(catalog_name)
        self.environment = Environment(
            self.dependencies, environment_name=environment_name, cache_path=self.cache_path_solution
        )

    def set_cache_paths(self, catalog_name):
        """Sets the available cache paths of the album object, given its catalog_name (where it lives)."""

        # Note: cache paths need the catalog the album live in - otherwise there might be problems with solutions
        # of different catalogs doing similar operations (e.g. downloads) as they might share the same cache path.
        path_suffix = Path("").joinpath(self["group"], self["name"], self["version"])
        self.cache_path_download = Configuration().cache_path_download.joinpath(str(catalog_name), path_suffix)
        self.cache_path_app = Configuration().cache_path_app.joinpath(str(catalog_name), path_suffix)
        self.cache_path_solution = Configuration().cache_path_solution.joinpath(str(catalog_name), path_suffix)

    def get_environment_name(self, catalog_name):
        return "_".join([str(catalog_name), self["group"], self["name"], self["version"]])
