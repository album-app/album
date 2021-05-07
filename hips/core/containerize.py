from hips.core import load_and_push_hips, pop_active_hips
from hips.core.model import logging

module_logger = logging.get_active_logger


# ToDo: implement
def containerize(args):
    """Function corresponding to the `containerize` subcommand of `hips`."""
    # Load HIPS
    active_hips = load_and_push_hips(args.path)
    module_logger().info('This would containerize: %s...' % active_hips['name'])
    pop_active_hips()
