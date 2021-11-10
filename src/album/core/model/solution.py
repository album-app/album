import copy
from pathlib import Path

from album.core.model.configuration import Configuration
from album.core.model.coordinates import Coordinates
from album.runner import album_logging, AlbumRunner

module_logger = album_logging.get_active_logger


class Solution(AlbumRunner):
    """Extension of a album-runner album class."""
    # Note: deploy, setup- and API-keywords in the album-runner

    def get_deploy_dict(self):
        """Return a dictionary with the relevant deployment key/values for a given album."""
        d = {}

        for k in self.deploy_keys:
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

    def __init__(self, attrs=None):
        """Sets object attributes in setup_keywords.

        Args:
            attrs:
                Dictionary containing the attributes.
        """
        # Attributes from the solution.py
        super().__init__(attrs)
        self.coordinates = Coordinates(attrs["group"], attrs["name"], attrs["version"])

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __eq__(self, other):
        return isinstance(other, Solution) and \
            other.coordinates == self.coordinates

    def get_arg(self, k):
        """Get a specific named argument for this solution if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]

    def set_cache_paths(self, catalog_name):
        """Sets the available cache paths of the album object, given its catalog_name (where it lives)."""

        # Note: cache paths need the catalog the album live in - otherwise there might be problems with solutions
        # of different catalogs doing similar operations (e.g. downloads) as they might share the same cache path.
        path_suffix = Path("").joinpath(self["group"], self["name"], self["version"])
        self.data_path = Configuration().cache_path_download.joinpath(str(catalog_name), path_suffix)
        self.app_path = Configuration().cache_path_app.joinpath(str(catalog_name), path_suffix)
        self.package_path = Configuration().cache_path_solution.joinpath(str(catalog_name), path_suffix)
        self.cache_path = Configuration().cache_path_tmp.joinpath(str(catalog_name), path_suffix)

    def get_cmdline_info(self, load_path) -> str:
        deploy_dict = self.get_deploy_dict()
        param_example_str = ''
        for arg in deploy_dict['args']:
            param_example_str += '--%s PARAMETER_VALUE ' % arg['name']
        res = 'Solution details about %s:\n\n' % load_path
        res += '%s\n' % self.title
        res += '%s\n' % ('=' * len(self.title))
        res += '%s\n\n' % self.description
        res += 'Group            : %s\n' % self.group
        res += 'Name             : %s\n' % self.name
        res += 'Version          : %s\n' % self.version
        res += '\nSolution credits:\n\n'
        res += '%s\n' % self.get_credit_as_string()
        res += 'Solution metadata:\n\n'
        res += 'Solution authors : %s\n' % ", ".join(self.authors)
        res += 'License          : %s\n' % self.license
        res += 'GIT              : %s\n' % self.git_repo
        res += 'Tags             : %s\n' % ", ".join(self.tags)
        res += '\n'
        res += 'Usage:\n\n'
        res += '  album install %s\n' % load_path
        res += '  album run %s %s\n' % (self.coordinates, param_example_str)
        res += '  album test %s\n' % self.coordinates
        res += '  album uninstall %s\n' % self.coordinates
        res += '\n'
        res += 'Run parameters:\n\n'
        for arg in deploy_dict['args']:
            res += '  --%s: %s\n' % (arg["name"], arg["description"])

        return res

    def get_credit_as_string(self) -> str:
        res = ""
        for citation in self.cite:
            text = citation['text']
            if 'doi' in citation:
                text += ' (DOI: %s)' % citation['doi']
            res += '%s\n' % text

        return res
