import hips
from utils import hips_logging

module_logger = hips_logging.get_active_logger


def remove(args):
    """Function corresponding to the `remove` subcommand of `hips`."""
    active_hips = hips.load_and_push_hips(args.path)
    module_logger().info('This would remove: %s' % active_hips['name'])
    hips.pop_active_hips()