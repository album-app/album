from hips.core import load_and_push_hips, pop_active_hips
from hips.core.model import logging

module_logger = logging.get_active_logger


def remove(args):
    """Function corresponding to the `remove` subcommand of `hips`."""
    active_hips = load_and_push_hips(args.path)
    module_logger().info('This would remove: %s' % active_hips['name'])
    pop_active_hips()