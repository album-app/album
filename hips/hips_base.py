from enum import unique, Enum

from hips_utils import hips_logging

module_logger = hips_logging.get_active_logger


@unique
class HipsDefaultValues(Enum):
    """Add a entry here to initialize default attributes for a hips object.

     Takes the Enum name as attribute name and the Enum value as default value.
     """
    catalog = 'https://gitlab.com/ida-mdc/hips-catalog.git'
    local_catalog_name = 'catalog_local'
    catalog_index_file_name = 'catalog_index'
    hips_config_file_name = '.hips-config'


class HipsClass:
    """Encapsulates a HIPS."""
    setup_keywords = ('group', 'name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'run', 'install', 'author', 'author_email',
                      'long_description', 'git_repo', 'dependencies',
                      'timestamp', 'format_version', 'authors', 'cite', 'tags',
                      'documentation', 'covers', 'sample_inputs',
                      'sample_outputs', 'doi', 'catalog', 'parent', 'steps', 'close', 'title')

    private_setup_keywords = ('_environment_name', '_environment_path',
                              '_repository_path', '_script')

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

    def __str__(self, indent=2):
        s = '\n'
        for attr in self.setup_keywords:
            if attr in dir(self):
                for ident in range(0, indent):
                    s += '\t'
                s += (attr + ':\t' + str(getattr(self, attr))) + '\n'
        return s

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, key, value):
        if key in self.private_setup_keywords:
            setattr(self, key, value)

    def get_arg(self, k):
        """Get a specific named argument for this hips if it exists."""
        matches = [arg for arg in self['args'] if arg['name'] == k]
        return matches[0]


