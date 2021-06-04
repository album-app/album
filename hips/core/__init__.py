import sys

from hips.core.model.hips_base import HipsClass
from hips_runner import logging

module_logger = logging.get_active_logger

"""
Global variable for tracking the currently active HIPS. Do not use this 
directly instead use get_active_hips()
"""
global _active_hips
_active_hips = []


def setup_hips(**attrs):
    """This configures a HIPS to for use by the main HIPS tool."""
    global _active_hips
    next_hips = HipsClass(attrs)
    push_active_hips(next_hips)


# overwrite hips_runner setup with this setup
sys.modules['hips_runner'].setup = setup_hips


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
    with open(path, "r") as f:
        hips_script = f.read()
    exec(hips_script)
    active_hips = get_active_hips()
    active_hips.script = hips_script
    return active_hips


def load(path):
    module_logger().debug(f'Loading HIPS from {path}...')
    with open(path, "r") as f:
        hips_script = f.read()
    exec(hips_script)
    active_hips = get_active_hips()
    active_hips.script = hips_script
    pop_active_hips()
    return active_hips
