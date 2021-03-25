import argparse
import sys

from hips import hips_debug
from hips.containerize import containerize
from hips.deploy import deploy
from hips.install import install
from hips.remove import remove
from hips.repl import repl
from hips.run import run
from hips.search import search
from hips.tutorial import tutorial
from utils import hips_logging

module_logger = hips_logging.get_active_logger


def main():
    """Entry points of `hips`."""

    __retrieve_logger()
    parser = create_parser()

    # ToDo: clean all hips environments

    module_logger().debug('Parsing base hips call arguments...')
    args = parser.parse_known_args()
    __handle_args(args, parser)


def __handle_args(args, parser):
    """Handles all arguments provided after the hips command."""
    hips_logging.set_loglevel(args[0].log)
    __run_subcommand(args, parser)


def __run_subcommand(args, parser):
    """Calls a specific hips subcommand."""
    hips_command = ""
    try:
        hips_command = sys.argv[1]  # hips command always expected at second position
    except IndexError:
        parser.error("Please provide a valid action!")
    module_logger().debug("Running %s subcommand..." % hips_command)
    sys.argv = [sys.argv[0]] + args[1]
    args[0].func(args[0])  # execute entry point function


def __retrieve_logger():
    """Retrieves the default hips logger."""
    hips_logging.configure_logging(hips_logging.LogLevel(hips_debug()), 'hips_core')


def create_parser():
    """Creates a parser for all known hips arguments."""
    parser = __HIPSParser()
    parser.create_command_parser('search', search, 'search for a HIP Solution using keywords')
    parser.create_hips_file_command_parser('run', run, 'run a HIP Solution')
    parser.create_hips_file_command_parser('repl', repl, 'get an interactive repl for a HIP Solution')
    parser.create_hips_file_command_parser('deploy', deploy, 'deploy a HIP Solution')
    parser.create_hips_file_command_parser('install', install, 'install a HIP Solution')
    parser.create_hips_file_command_parser('remove', remove, 'remove a HIP Solution')
    parser.create_hips_file_command_parser('containerize', containerize, 'create a Singularity container for a HIP Solution')
    parser.create_hips_file_command_parser('tutorial', tutorial, 'run a tutorial for a HIP Solution')
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
        self.subparsers = self.parser.add_subparsers(title='actions', help='sub-command help')

    @staticmethod
    def __create_parent_parser():
        """Parent parser for all subparsers to have the same set of arguments."""
        parent_parser = ArgumentParser(add_help=False)
        # parse logging
        parent_parser.add_argument(
            '--log',
            required=False,
            help='Logging level for your hips command. Choose between %s' %
                 ", ".join([loglevel.name for loglevel in hips_logging.LogLevel]),
            default=hips_logging.LogLevel(hips_debug()),
            type=(lambda choice: hips_logging.to_loglevel(choice)),
        )
        return parent_parser

    def __create_hips_parser(self):
        """Creates the main parser for the hip framework."""
        parser = ArgumentParser(
            add_help=False,
            description='Helmholtz Imaging Platform (HIP) Solutions framework for running, building,'
                        ' and deploying generalized imaging solutions',
            parents=[self.parent_parser]
        )
        return parser

    def create_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a hips command, specified by a name, a function and a help description."""
        parser = self.subparsers.add_parser(
            command_name, help=command_help, parents=[self.parent_parser])
        parser.set_defaults(func=command_function)
        return parser

    def create_hips_file_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a hips command dealing with a hips file.

        Parser is specified by a name, a function and a help description.
        """
        parser = self.create_command_parser(command_name, command_function, command_help)
        parser.add_argument('path',
                            type=str,
                            help='path for the HIPS file')
        return parser


if __name__ == "__main__":
    main()
