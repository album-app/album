from hips.hips_base import HipsClass
from hips_utils import hips_logging

DEBUG = False
module_logger = hips_logging.get_active_logger


def hips_debug():
    return DEBUG


"""
Global variable for tracking the currently active HIPS. Do not use this 
directly instead use get_active_hips()
"""
global _active_hips
_active_hips = []


def setup(**attrs):
    """This configures a HIPS to for use by the main HIPS tool."""
    global _active_hips
    next_hips = HipsClass(attrs)
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
    with open(path, "r") as f:
        hips_script = f.read()
    exec(hips_script)
    active_hips = get_active_hips()
    active_hips.script = hips_script
    return active_hips


def notify_hips_started(active_hips, subprocess=False):
    msg = "Started %s..." % active_hips['name']
    if subprocess:
        print(msg)
    else:
        module_logger().info(msg)


def notify_active_hips_started(subprocess=False):
    notify_hips_started(get_active_hips(), subprocess)


def notify_active_hips_finished(subprocess=False):
    msg = "Finished running %s." % get_active_hips()['name']
    if subprocess:
        print(msg)
    else:
        module_logger().info(msg)


def notify_active_hips_progress(message, current_step, max_steps, subprocess=False):
    msg = "%s %s / %s" % (message, current_step, max_steps)
    if subprocess:
        print(msg)
    else:
        module_logger().info(msg)
