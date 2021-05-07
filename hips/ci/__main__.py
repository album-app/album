from argparse import ArgumentParser

from hips.ci import pre_release
from hips.ci import release
from hips.core.model import logging

module_logger = logging.get_active_logger

entry_point_map = {
    'ci_pre_release': pre_release.ci_pre_release,
    'ci_release': release.ci_release
}


def __retrieve_logger():
    """Retrieves the default hips logger."""
    logging.configure_logging(logging.LogLevel.DEBUG, 'hips_ci')


def create_parser():
    parser = ArgumentParser(add_help=False)
    # parse logging
    parser.add_argument(
        'ci_routine',
        help='Which ci routine to perform',
        default='ci_pre_release',
    )
    return parser


if __name__ == '__main__':
    # configure logging for hips CI
    __retrieve_logger()

    ci_parser = create_parser()
    args = ci_parser.parse_args()

    module_logger().info("Starting CI release cycle...")

    # read out entry point
    entry_point = entry_point_map[args.ci_routine]

    entry_point()
