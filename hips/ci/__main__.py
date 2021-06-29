from argparse import ArgumentParser

from hips.ci.controller.release_manager import ReleaseManager
from hips_runner.logging import get_active_logger, configure_logging, LogLevel

module_logger = get_active_logger

release_manager = ReleaseManager()

entry_point_map = {
    'ci_pre_release': release_manager.pre_release,
    'ci_release': release_manager.release()
}


def __retrieve_logger():
    """Retrieves the default hips logger."""
    configure_logging(LogLevel.DEBUG, 'hips_ci')


def create_parser():
    parser = ArgumentParser(add_help=False)
    # parse logging
    parser.add_argument(
        'ci_routine',
        help='Which ci routine to perform',
        default='ci_pre_release',
    )
    parser.add_argument(
        '--dry-run',
        required=False,
        help='Dry-run option. If True, no merge request will be created, only infor is shown. Choose between %s' %
             ", ".join([str(True), str(False)]),
        default=False,
        type=(lambda choice: bool(choice)),
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
