from hips.core import load_and_push_hips, pop_active_hips
from hips.core.model import logging

module_logger = logging.get_active_logger


def tutorial(args):
    """Function corresponding to the `tutorial` subcommand of `hips`."""
    active_hips = load_and_push_hips(args.path)
    module_logger().info('This would run a tutorial for: %s...' % active_hips['name'])
    pop_active_hips()
