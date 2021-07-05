import argparse
import sys

from hips.core.commandline import add_catalog, remove_catalog, containerize, deploy, install, remove, repl, run, search, \
    start_server, tutorial, test
from hips_runner import logging
from hips_runner.logging import hips_debug

module_logger = logging.get_active_logger


def main():
    """Entry points of `hips`."""
    parser = create_parser()

    # ToDo: clean all hips environments

    module_logger().debug('Parsing base hips call arguments...')
    args = parser.parse_known_args()
    __handle_args(args, parser)


def __handle_args(args, parser):
    """Handles all arguments provided after the hips command."""
    logging.set_loglevel(args[0].log)
    __run_subcommand(args, parser)


def __run_subcommand(args, parser):
    """Calls a specific hips subcommand."""
    hips_command = ""
    try:
        hips_command = sys.argv[
            1]  # hips command always expected at second position
    except IndexError:
        parser.error("Please provide a valid action!")
    module_logger().debug("Running %s subcommand..." % hips_command)
    sys.argv = [sys.argv[0]] + args[1]
    args[0].func(args[0])  # execute entry point function


def create_parser():
    """Creates a parser for all known hips arguments."""
    parser = __HIPSParser()
    p = parser.create_command_parser(
        'search', search, 'search for a HIP Solution using keywords')
    p.add_argument('keywords', type=str, nargs='+', help='Search keywords')
    p = parser.create_hips_file_command_parser('run', run,
                                               'run a HIP Solution')
    p.add_argument(
        '--run-immediately',
        required=False,
        help=
        'When the solution to run consists of several steps, indicates whether to immediately run '
        'a step (True) or to wait for all steps to be prepared to run (False). Choose between %s.'
        ' Default is False' % ", ".join([str(True), str(False)]),
        default=False,
        type=(lambda choice: bool(choice)))
    parser.create_hips_file_command_parser(
        'repl', repl, 'get an interactive repl for a HIP Solution')
    p = parser.create_hips_file_command_parser('deploy', deploy,
                                               'deploy a HIP Solution')
    p.add_argument(
        '--dry-run',
        required=False,
        help=
        'Boolean to indicate a dry run and only show what would happen. Choose between %s.'
        ' Default is False' % ", ".join([str(True), str(False)]),
        default=False,
        type=(lambda choice: bool(choice)))
    p.add_argument(
        '--catalog',
        required=False,
        help='Specify a catalog ID to deploy to. Must be configured! '
        '\"catalog_local\" refers to the local catalog. Default is None',
        default=None)
    p.add_argument(
        '--trigger-pipeline',
        required=False,
        help=
        'Boolean to indicate whether to trigger the CI of the catlog or not! Choose between %s. '
        'Default is True' % ", ".join([str(True), str(False)]),
        default=True,
        type=(lambda choice: bool(choice)))
    p.add_argument(
        '--git-email',
        required=False,
        help='Email to use for all git operations. '
        'If none given, system is required to be proper configured!',
        default=None)
    p.add_argument(
        '--git-name',
        required=False,
        help='Name to use for all git operations. '
        'If none given, system is required to be proper configured!',
        default=None)

    parser.create_hips_file_command_parser('install', install,
                                           'install a HIP Solution')
    p = parser.create_hips_file_command_parser('remove', remove,
                                               'remove a HIP Solution')
    p.add_argument(
        '--remove-deps',
        required=False,
        help=
        'Boolean to additionally remove all hips dependencies. Choose between %s'
        % ", ".join([str(True), str(False)]),
        default=False,
        type=(lambda choice: bool(choice)))
    parser.create_hips_file_command_parser(
        'containerize', containerize,
        'create a Singularity container for a HIP Solution')
    parser.create_hips_file_command_parser(
        'tutorial', tutorial, 'run a tutorial for a HIP Solution')
    parser.create_hips_file_command_parser(
        'add-catalog', add_catalog,
        'add a catalog to your local HIPS configuration file')
    parser.create_hips_file_command_parser(
        'remove-catalog', remove_catalog,
        'remove a catalog from your local HIPS configuration file')
    parser.create_hips_file_command_parser(
        'test', test, 'execute a solutions test routine.')
    p = parser.create_command_parser('server', start_server,
                                     'start a HIPS server')
    p.add_argument('port', type=int, default=8080, help='Port')
    return parser.parser


class ArgumentParser(argparse.ArgumentParser):
    """Override default error method of all parsers to show help of subcommand"""
    def error(self, message):
        self.print_help()
        self.exit(2, '%s: error: %s\n' % (self.prog, message))


class __HIPSParser(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.parent_parser = self.__create_parent_parser()
        self.parser = self.__create_hips_parser()
        self.subparsers = self.parser.add_subparsers(title='actions',
                                                     help='sub-command help')

    @staticmethod
    def __create_parent_parser():
        """Parent parser for all subparsers to have the same set of arguments."""
        parent_parser = ArgumentParser(add_help=False)
        # parse logging
        parent_parser.add_argument(
            '--log',
            required=False,
            help='Logging level for your hips command. Choose between %s' %
            ", ".join([loglevel.name for loglevel in logging.LogLevel]),
            default=logging.LogLevel(hips_debug()),
            type=(lambda choice: logging.to_loglevel(choice)),
        )
        return parent_parser

    def __create_hips_parser(self):
        """Creates the main parser for the hip framework."""
        parser = ArgumentParser(
            add_help=True,
            description=
            'album for running, building, and deploying computational solutions',
            parents=[self.parent_parser])
        return parser

    def create_command_parser(self, command_name, command_function,
                              command_help):
        """Creates a parser for a hips command, specified by a name, a function and a help description."""
        parser = self.subparsers.add_parser(command_name,
                                            help=command_help,
                                            parents=[self.parent_parser])
        parser.set_defaults(func=command_function)
        return parser

    def create_hips_file_command_parser(self, command_name, command_function,
                                        command_help):
        """Creates a parser for a hips command dealing with a hips file.

        Parser is specified by a name, a function and a help description.
        """
        parser = self.create_command_parser(command_name, command_function,
                                            command_help)
        parser.add_argument('path', type=str, help='path for the HIPS file')
        return parser


if __name__ == "__main__":
    main()
