import copy
from hips.core.model import logging
from hips.core.model.environment import Environment

module_logger = logging.get_active_logger


class HipsClass:
    """Encapsulates a HIPS."""

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
                if "action" in arg.keys():
                    arg.pop("action")

        return hips_dict

    setup_keywords = ('group', 'name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'run', 'install', 'author', 'author_email',
                      'long_description', 'git_repo', 'dependencies',
                      'timestamp', 'format_version', 'authors', 'cite', 'tags',
                      'documentation', 'covers', 'sample_inputs',
                      'sample_outputs', 'doi', 'catalog', 'parent', 'steps', 'close', 'title')

    private_setup_keywords = ('_repository_path', '_script')

    # default values
    dependencies = None
    parent = None

    def __init__(self, attrs=None):
        """sets object attributes in setup_keywords

        Args:
            attrs:
                Dictionary containing the attributes.
        """
        # Attributes from the solution.py
        for attr in self.setup_keywords:
            if attr in attrs:
                setattr(self, attr, attrs[attr])

        # Attributes only available in the hips environment.
        for private_attr in self.private_setup_keywords:
            setattr(self, private_attr, "")

        self.environment = Environment(self.get_hips_deploy_dict())

    def __str__(self, indent=2):
        s = '\n'
        for attr in self.setup_keywords:
            if attr in dir(self):
                for ident in range(0, indent):
                    s += '\t'
                s += (attr + ':\t' + str(getattr(self, attr))) + '\n'
        return s

    def __getitem__(self, k):
        if hasattr(self, k):
            return getattr(self, k)
        return None

    def __setitem__(self, key, value):
        if key in self.private_setup_keywords:
            setattr(self, key, value)

    def get_arg(self, k):
        """Get a specific named argument for this hips if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]


