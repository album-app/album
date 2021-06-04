import copy

from hips.core.model.configuration import HipsConfiguration
from hips.core.model.environment import Environment
from hips_runner import logging
from hips_runner import HipsRunner

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

        self.environment = Environment(
            self.dependencies, self["name"],  HipsConfiguration().get_cache_path_hips(self)
        )

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get_arg(self, k):
        """Get a specific named argument for this hips if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]


