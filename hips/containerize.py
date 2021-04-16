import hips
from hips_utils import hips_logging

module_logger = hips_logging.get_active_logger


def containerize(args):
    """Function corresponding to the `containerize` subcommand of `hips`."""
    # Load HIPS
    active_hips = hips.load_and_push_hips(args.path)
    module_logger().info('This would containerize: %s' % active_hips['name'])
    hips.pop_active_hips()
