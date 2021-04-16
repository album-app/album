import hips
from hips_utils import hips_logging

module_logger = hips_logging.get_active_logger


def tutorial(args):
    """Function corresponding to the `tutorial` subcommand of `hips`."""
    active_hips = hips.load_and_push_hips(args.path)
    module_logger().info('This would run a tutorial for: %s' % active_hips['name'])
    hips.pop_active_hips()
