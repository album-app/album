from enum import Enum, unique

from utils import hips_logging

DEBUG = False
module_logger = hips_logging.get_active_logger


def hips_debug():
    return DEBUG


@unique
class HipsDefaultValues(Enum):
    """Add a entry here to initialize default attributes for a hips object.

     Takes the Enum name as attribute name and the Enum value as default value.
     """
    catalog = 'https://gitlab.com/ida-mdc/hips-catalog.git'


class Hips:
    """Encapsulates a HIPS."""
    setup_keywords = ('group', 'name', 'version', 'description', 'url', 'license',
                      'min_hips_version', 'tested_hips_version', 'args',
                      'init', 'run', 'install', 'author', 'author_email',
                      'long_description', 'git_repo', 'dependencies',
                      'timestamp', 'format_version', 'authors', 'cite', 'tags',
                      'documentation', 'covers', 'sample_inputs',
                      'sample_outputs', 'doi', 'catalog', 'parent', 'steps', 'close')

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

        # Default attributes
        for defaultAttribute in HipsDefaultValues:
            if defaultAttribute.name not in attrs:
                module_logger().info("Attribute %s not specified. Set it to %s" %
                                   (defaultAttribute.name, defaultAttribute.value))
                setattr(self, defaultAttribute.name, defaultAttribute.value)

        # Attributes only available in the hips environment.
        for private_attr in self.private_setup_keywords:
            setattr(self, private_attr, "")

    def __str__(self):
        s = ''
        for attr in self.setup_keywords:
            if attr in dir(self):
                s += (attr + '\t' + str(getattr(self, attr))) + '\n'
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


"""
Global variable for tracking the currently active HIPS. Do not use this 
directly instead use get_active_hips()
"""
global _active_hips
_active_hips = []


def setup(**attrs):
    """This configures a HIPS to for use by the main HIPS tool."""
    global _active_hips
    next_hips = Hips(attrs)
    push_active_hips(next_hips)


def push_active_hips(hips_object):
    """Pop a hips to the _active_hips stack."""
    global _active_hips
    _active_hips.insert(0, hips_object)


def get_parent_hips():
    """Return the parent HIPS of the currently active HIPS."""
    global _active_hips
    if len(_active_hips) > 1:
        return _active_hips[1]
    return None


def get_active_hips():
    """Return the currently active HIPS, which is defined globally."""
    global _active_hips
    if len(_active_hips) > 0:
        return _active_hips[0]
    return None


def pop_active_hips():
    """Pop the currently active hips from the _active_hips stack."""
    global _active_hips

    if len(_active_hips) > 0:
        return _active_hips.pop(0)
    else:
        return None


def load_and_push_hips(path):
    """Load hips script"""
    module_logger().debug(f'Loading HIPS from {path}...')
    hips_script = open(path).read()
    exec(hips_script)
    active_hips = get_active_hips()
    active_hips.script = hips_script
    module_logger().debug('hips loaded locally: %s' % str(active_hips))
    return active_hips
