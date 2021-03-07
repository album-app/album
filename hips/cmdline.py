import sys
import argparse
from hips import hips_debug
from hips.deploy import deploy
from hips.run import run
from hips.repl import repl
from hips.search import search
from hips.install import install
from hips.remove import remove
from hips.containerize import containerize
from hips.tutorial import tutorial

import logging
from utils import hips_logging


module_logger = logging.getLogger('hips')


def main():
    """Entry points of `hips`."""

    retrieve_logger()
    parser = create_parser()

    # ToDo: clean all hips environments

    module_logger.debug('Parsing base hips call arguments...')
    handle_args(parser.parse_known_args())


def handle_args(args):
    hips_logging.set_loglevel(args[0].log, 'hips')
    run_subcommand(args)


def run_subcommand(args):
    hips_command = sys.argv[1]
    module_logger.debug("Running %s subcommand..." % hips_command)
    sys.argv = ["None"] + args[1]
    args[0].func(args[0])


def retrieve_logger():
    hips_logging.configure_logging(hips_logging.LogLevel(hips_debug()), 'hips')


def create_parser():
    parser = HIPSParser()
    parser.create_command_parser('search', search, 'search for a HIP Solution using keywords')
    parser.create_hips_file_command_parser('run', run, 'run a HIP Solution')
    parser.create_hips_file_command_parser('repl', repl, 'get an interactive repl for a HIP Solution')
    parser.create_hips_file_command_parser('deploy', deploy, 'deploy a HIP Solution')
    parser.create_hips_file_command_parser('install', install, 'install a HIP Solution')
    parser.create_hips_file_command_parser('remove', remove, 'remove a HIP Solution')
    parser.create_hips_file_command_parser('containerize', containerize, 'create a Singularity container for a HIP Solution')
    parser.create_hips_file_command_parser('tutorial', tutorial, 'run a tutorial for a HIP Solution')
    return parser.parser


class HIPSParser:

    def __init__(self):
        self.parent_parser = self.create_parent_parser()
        self.parser = self.create_hips_parser()
        self.subparsers = self.parser.add_subparsers(title='actions', help='sub-command help')

        parser = argparse.ArgumentParser(
    @staticmethod
    def create_hips_parser():
            add_help=False,
            description=
            'Helmholtz Imaging Platform (HIP) Solutions framework for running, building, and deploying generalized imaging solutions'
        )
        return parser

    @staticmethod
    def create_parent_parser():
        parent_parser = argparse.ArgumentParser(add_help=False)
        # parse logging
        parent_parser.add_argument(
            '--log',
            required=False,
            help='Logging level for your hips command. Choose between %s' %
                 ", ".join([loglevel.name for loglevel in hips_logging.LogLevel]),
            default='INFO',
            type=(lambda choice: hips_logging.to_loglevel(choice, 'hips')),
        )
        return parent_parser

    def create_command_parser(self, command_name, command_function, command_help):
        parser = self.subparsers.add_parser(
            command_name, help=command_help, parents=[self.parent_parser])
        parser.set_defaults(func=command_function)
        return parser

    def create_hips_file_command_parser(self, command_name, command_function, command_help):
        parser = self.create_command_parser(command_name, command_function, command_help)
        parser.add_argument('path',
                            type=str,
                            help='path for the HIPS file')
        return parser


if __name__ == "__main__":
    main()
