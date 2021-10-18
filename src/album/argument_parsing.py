import argparse
import sys

from album.api import Album
from album.core.commandline import add_catalog, remove_catalog, deploy, \
    install, repl, run, search, start_server, test, update, clone, upgrade, index, uninstall
from album.runner import logging
from album.runner.logging import debug_settings

module_logger = logging.get_active_logger


def main():
    """Entry points of `album`."""

    parser = create_parser()

    # ToDo: clean all album environments

    module_logger().debug('Parsing base album call arguments...')
    args = parser.parse_known_args()
    __handle_args(args, parser)


def __handle_args(args, parser):
    """Handles all arguments provided after the album command."""
    logging.set_loglevel(args[0].log)
    __run_subcommand(args, parser)


def __run_subcommand(args, parser):
    """Calls a specific album subcommand."""
    album_command = ""
    try:
        album_command = sys.argv[1]  # album command always expected at second position
    except IndexError:
        parser.error("Please provide a valid action!")
    module_logger().debug("Running %s subcommand..." % album_command)
    sys.argv = [sys.argv[0]] + args[1]

    # Makes sure album is initialized.
    Album()

    args[0].func(args[0])  # execute entry point function


def create_parser():
    """Creates a parser for all known album arguments."""
    parser = AlbumParser()
    p = parser.create_command_parser('search', search, 'search for an album solution using keywords')
    p.add_argument('keywords', type=str, nargs='+', help='Search keywords')
    p = parser.create_file_command_parser('run', run, 'run an album solution')
    p.add_argument(
        '--run-immediately',
        required=False,
        help='When the solution to run consists of several steps, indicates whether to immediately run '
             'a step or to wait for all steps to be prepared to run.',
        default=False,
        action='store_true')
    parser.create_file_command_parser('repl', repl, 'get an interactive repl for an album solution')
    p = parser.create_file_command_parser('deploy', deploy, 'deploy an album solution')
    p.add_argument(
        '--dry-run',
        required=False,
        help='Parameter to indicate a dry run and only show what would happen.',
        action='store_true'
    )
    p.add_argument(
        '--catalog',
        required=False,
        help='Specify a catalog name to deploy to. Must be configured! '
             '\"catalog_local\" refers to the local catalog. Default is None.',
        default=None)
    p.add_argument(
        '--push-option',
        required=False,
        help='Push options for the catalog repository.',
        default=None,
    )
    p.add_argument(
        '--git-email',
        required=False,
        help='Email to use for all git operations. If none given, system is required to be proper configured!',
        default=None
    )
    p.add_argument(
        '--git-name',
        required=False,
        help='Name to use for all git operations. If none given, system is required to be proper configured!',
        default=None
    )

    parser.create_file_command_parser('install', install, 'install an album solution')
    p = parser.create_file_command_parser('uninstall', uninstall, 'uninstall an album solution')
    p.add_argument(
        '--uninstall-deps',
        required=False,
        help=
        'Boolean to additionally remove all album dependencies. Choose between %s'
        % ", ".join([str(True), str(False)]),
        default=False,
        action='store_true'
    )
    parser.create_catalog_command_parser(
        'add-catalog', add_catalog,
        'add a catalog to your local album configuration file'
    )
    parser.create_catalog_command_parser(
        'remove-catalog', remove_catalog,
        'remove a catalog from your local album configuration file'
    )
    p = parser.create_command_parser(
        'update',
        update,
        'Update the catalog index files. Either all catalogs configured, or a specific one.'
    )
    p.add_argument('src', type=str, help='src of the catalog', nargs='?')
    p = parser.create_command_parser(
        'upgrade',
        upgrade,
        'upgrade the local collection from the catalog index files. Either all catalogs configured, or a specific one.'
    )
    p.add_argument('src', type=str, help='src of the catalog', nargs='?')
    p.add_argument(
        '--dry-run',
        required=False,
        help='Parameter to indicate a dry run and only show what would happen.',
        action='store_true'
    )
    p = parser.create_command_parser('clone', clone, 'clone an album solution or catalog template')
    p.add_argument('src', type=str,
                   help='path for the solution file, group:name:version or name of the catalog template')
    p.add_argument(
        '--target-dir',
        required=True,
        help='The target directory where the solution or catalog will be added to',
        default=None
    )
    p.add_argument(
        '--name',
        required=True,
        help='The new name of the cloned solution or catalog',
        default=None
    )
    parser.create_command_parser('index', index, 'print the index of the local album collection')
    parser.create_file_command_parser(
        'test', test, 'execute a solutions test routine.')
    p = parser.create_command_parser('server', start_server,
                                     'start an album server')
    p.add_argument('--port', type=int, required=False, default=8080, help='Port')
    p.add_argument('--host', type=str, required=False, default="127.0.0.1", help='Host')
    return parser.parser


class ArgumentParser(argparse.ArgumentParser):
    """Override default error method of all parsers to show help of subcommand"""

    def error(self, message):
        self.print_help()
        self.exit(2, '%s: error: %s\n' % (self.prog, message))


class AlbumParser(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.parent_parser = self.create_parent_parser()
        self.parser = self.create_parser()
        self.subparsers = self.parser.add_subparsers(title='actions', help='sub-command help')

    @staticmethod
    def create_parent_parser():
        """Parent parser for all subparsers to have the same set of arguments."""
        parent_parser = ArgumentParser(add_help=False)
        # parse logging
        parent_parser.add_argument(
            '--log',
            required=False,
            help='Logging level for your album command. Choose between %s' %
                 ", ".join([loglevel.name for loglevel in logging.LogLevel]),
            default=logging.LogLevel(debug_settings()),
            type=(lambda choice: logging.to_loglevel(choice)),
        )
        return parent_parser

    def create_parser(self):
        """Creates the main parser for the album framework."""
        parser = ArgumentParser(
            add_help=True,
            description=
            'album for running, building, and deploying computational solutions',
            parents=[self.parent_parser])
        return parser

    def create_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a album command, specified by a name, a function and a help description."""
        parser = self.subparsers.add_parser(command_name, help=command_help, parents=[self.parent_parser])
        parser.set_defaults(func=command_function)
        return parser

    def create_file_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a album command dealing with an album file.

        Parser is specified by a name, a function and a help description.
        """
        parser = self.create_command_parser(command_name, command_function, command_help)
        parser.add_argument('path', type=str, help='path for the solution file')
        return parser

    def create_catalog_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a album command dealing with an album catalog.

        Parser is specified by a name, a function and a help description.
        """
        parser = self.create_command_parser(command_name, command_function, command_help)
        parser.add_argument('src', type=str, help='src of the catalog')
        return parser


if __name__ == "__main__":
    main()