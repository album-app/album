import copy
from pathlib import Path

from hips.core.model.configuration import HipsConfiguration

from hips.core.model.environment import Environment
from hips_runner import HipsRunner
from hips_runner import logging

module_logger = logging.get_active_logger


class HipsClass(HipsRunner):
    """Extension of a HIPS-runner HIPS class."""

    # CAUTION: deploy_keys also used for resolving. Make sure keys do not contain callable values.
    # If they do, add "to_string" method for @get_hips_deploy_dict. Example see @_remove_action_from_args.
    deploy_keys = [
        'group', 'name', 'description', 'version', 'format_version', 'tested_hips_version',
        'min_hips_version', 'license', 'git_repo', 'authors', 'cite', 'tags', 'documentation',
        'covers', 'sample_inputs', 'sample_outputs', 'args', 'title'
    ]

    def get_hips_deploy_dict(self):
        """Return a dictionary with the relevant deployment key/values for a given hips."""
        d = {}

        for k in HipsClass.deploy_keys:
            # deepcopy necessary. Else original hips object will loose "action" attributes in its arguments
            d[k] = copy.deepcopy(self.__dict__[k])

        return self._remove_action_from_args(d)

    @staticmethod
    def _remove_action_from_args(hips_dict):
        for arg in hips_dict["args"]:
            if isinstance(arg, dict):
                # iterate and remove callable values
                for key in arg.keys():
                    if callable(arg[key]):
                        arg[key] = "%s_function" % key
        return hips_dict

    # setup- and API-keywords in the hips_runner

    def __init__(self, attrs=None):
        """sets object attributes in setup_keywords

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
        """Get a specific named argument for this hips if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]

    def set_environment(self, catalog_id):
        """Initializes the Environment of the solution. This is not an installation!"""
        self.set_cache_paths(catalog_id)
        self.environment = Environment(
            self.dependencies, cache_name=self["name"], cache_path=self.cache_path_solution
        )

    def set_cache_paths(self, catalog_id):
        """Sets the available cache paths of the hips object, given its catalog_id (where it lives)"""

        # Note: cache paths need the catalog the hips live in - otherwise there might be problems with solutions
        # of different catalogs doing similar operations (e.g. downloads) as they might share the same cache path.
        path_suffix = Path("").joinpath(self["group"], self["name"], self["version"])
        self.cache_path_download = HipsConfiguration().cache_path_download.joinpath(catalog_id, path_suffix)
        self.cache_path_app = HipsConfiguration().cache_path_app.joinpath(catalog_id, path_suffix)
        self.cache_path_solution = HipsConfiguration().cache_path_solution.joinpath(catalog_id, path_suffix)
