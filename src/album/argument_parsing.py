import argparse
import sys
import traceback

import pkg_resources

from album import core
from album.api import Album
from album.commandline import (
    add_catalog,
    remove_catalog,
    deploy,
    install,
    repl,
    run,
    search,
    test,
    update,
    clone,
    upgrade,
    index,
    uninstall,
    info,
    undeploy,
)
from album.core.utils.subcommand import SubProcessError
from album.runner.album_logging import (
    debug_settings,
    get_active_logger,
    LogLevel,
    to_loglevel,
)


def main():
    """Entry points of `album`."""

    parser = create_parser()

    get_active_logger().debug("Parsing base album call arguments...")
    namespace, args = parser.parse_known_args()
    __handle_args(namespace, args, parser)


def __handle_args(namespace, args, parser):
    """Handles all arguments provided after the album command."""
    level = namespace.log
    print_json = getattr(namespace, "json", False)
    __run_subcommand(namespace, args, parser, level, print_json)


def _capture_output():
    logger = get_active_logger()
    logger.handlers.clear()


def _handle_exception(e, silent: bool = False):
    if not silent:
        get_active_logger().error("album command failed: %s" % str(e))
        get_active_logger().debug(traceback.format_exc())
    if type(e) is int:
        sys.exit(e)
    elif hasattr(e, "exit_status"):
        sys.exit(e.exit_status)
    else:
        sys.exit(e)


def __run_subcommand(namespace, args, parser, level: LogLevel, print_json):
    """Calls a specific album subcommand."""
    album_command = ""
    try:
        album_command = sys.argv[1]  # album command always expected at second position
    except IndexError:
        parser.error("Please provide a valid action!")
    get_active_logger().debug("Running %s subcommand..." % album_command)
    sys.argv = [sys.argv[0]] + args

    # Makes sure album is initialized.
    album_instance = create_album_instance(level)
    if print_json:
        _capture_output()
    get_active_logger().info("album version %s" % core.__version__)

    try:
        if hasattr(namespace, "func"):
            album_instance.load_or_create_collection()
            namespace.func(album_instance, namespace)  # execute entry point function
        else:
            get_active_logger().error("Invalid argument(s): %s" % args)
            sys.exit(1)
    except KeyboardInterrupt:
        get_active_logger().error("Album command canceled.")
        sys.exit(1)
    except SubProcessError as e:
        _handle_exception(e, silent=True)
    except Exception as e:
        _handle_exception(e)


def create_album_instance(level: LogLevel) -> Album:
    return Album.Builder().log_level(level).build()


def create_parser():
    """Creates a parser for all known album arguments."""
    parser = AlbumParser()
    parser_creators = []
    for entry_point in pkg_resources.iter_entry_points("console_parsers_album"):
        try:
            parser_creators.append(entry_point.load())
        except Exception as e:
            get_active_logger().error(
                "Cannot load console parser %s" % entry_point.name
            )
            get_active_logger().debug(str(e))
    for parse_creator in parser_creators:
        parse_creator(parser)
    return parser.parser


def create_test_parser(parser):
    parser.create_file_command_parser(
        "test", test, "execute the test routine of a solution."
    )


def create_index_parser(parser):
    parser.create_command_parser(
        "index", index, "print the index of the local album collection."
    )


def create_clone_parser(parser):
    p = parser.create_command_parser(
        "clone", clone, "clone an album solution or catalog template."
    )
    p.add_argument(
        "src",
        type=str,
        help="path for the solution file, group:name:version or name of the catalog template.",
    )
    p.add_argument(
        "target_dir",
        type=str,
        help="The target directory where the solution or catalog will be added to. For a catalog, this can also be an empty GIT repository URL.",
    )
    p.add_argument(
        "name", type=str, help="The new name of the cloned solution or catalog."
    )


def create_upgrade_parser(parser):
    p = parser.create_command_parser(
        "upgrade",
        upgrade,
        "upgrade the local collection from the catalog index files. Either all catalogs configured, or a specific one.",
    )
    p.add_argument("catalog", type=str, help="name of the catalog", nargs="?")
    p.add_argument(
        "--dry-run",
        required=False,
        help="Parameter to indicate a dry run and only show what would happen.",
        action="store_true",
    )
    p.add_argument(
        "--override",
        required=False,
        help="renews all installed solutions without re-installation. "
        "Might produce dependency problems as environments are not updated. Handle with care.",
        action="store_true",
    )


def create_update_parser(parser):
    p = parser.create_command_parser(
        "update",
        update,
        "Update the catalog index files. Either all catalogs configured, or a specific one.",
    )
    p.add_argument("catalog", type=str, help="name of the catalog", nargs="?")


def create_remove_catalog_parser(parser):
    p = parser.create_command_parser(
        "remove-catalog",
        remove_catalog,
        "remove a catalog from your local album configuration file.",
    )
    p.add_argument("name", type=str, help="name of the catalog")


def create_add_catalog_parser(parser):
    p = parser.create_command_parser(
        "add-catalog",
        add_catalog,
        "add a catalog to your local album configuration file.",
    )
    p.add_argument("src", type=str, help="src of the catalog")


def create_info_parser(parser):
    parser.create_file_command_parser(
        "info", info, "print information about an album solution."
    )


def create_uninstall_parser(parser):
    p = parser.create_file_command_parser(
        "uninstall", uninstall, "uninstall an album solution."
    )
    p.add_argument(
        "--uninstall-deps",
        required=False,
        help="Boolean to additionally remove all album dependencies. Choose between %s."
        % ", ".join([str(True), str(False)]),
        default=False,
        action="store_true",
    )


def create_install_parser(parser):
    parser.create_file_command_parser("install", install, "install an album solution.")


def create_deploy_parser(parser):
    p = parser.create_file_command_parser("deploy", deploy, "deploy an album solution.")
    p.add_argument(
        "catalog",
        type=str,
        help="Specify a catalog name to deploy to. Must be configured!",
    )
    p.add_argument(
        "--dry-run",
        required=False,
        help="Parameter to indicate a dry run and only show what would happen.",
        action="store_true",
    )
    p.add_argument(
        "--push-option",
        required=False,
        help="Push options for the catalog repository.",
        default=None,
        nargs="+",
    )
    p.add_argument(
        "--git-email",
        required=False,
        help="Email to use for all git operations. If none given, system is required to be proper configured!",
        default=None,
    )
    p.add_argument(
        "--git-name",
        required=False,
        help="Name to use for all git operations. If none given, system is required to be proper configured!",
        default=None,
    )
    p.add_argument(
        "--force-deploy",
        required=False,
        help="When specified,force deploys a solution to a catalog."
        " Useful if the solution has already been deployed once.",
        action="store_false",
    )
    p.add_argument(
        "--changelog",
        required=False,
        help="Description of changes from the previous version of the solution to this version.",
        default=None,
    )


def create_undeploy_parser(parser):
    p = parser.create_file_command_parser(
        "undeploy", undeploy, "undeploy an album solution."
    )
    p.add_argument(
        "catalog",
        type=str,
        help="Specify a catalog name to remove the solution from. Must be configured!",
    )
    p.add_argument(
        "--dry-run",
        required=False,
        help="Parameter to indicate a dry run and only show what would happen.",
        action="store_true",
    )
    p.add_argument(
        "--push-option",
        required=False,
        help="Push options for the catalog repository.",
        default=None,
        nargs="+",
    )
    p.add_argument(
        "--git-email",
        required=False,
        help="Email to use for all git operations. If none given, system is required to be proper configured!",
        default=None,
    )
    p.add_argument(
        "--git-name",
        required=False,
        help="Name to use for all git operations. If none given, system is required to be proper configured!",
        default=None,
    )


def create_repl_parser(parser):
    parser.create_file_command_parser(
        "repl", repl, "get an interactive repl for an album solution."
    )


def create_run_parser(parser):
    parser.create_file_command_parser("run", run, "run an album solution.")


def create_search_parser(parser):
    p = parser.create_command_parser(
        "search", search, "search for an album solution using keywords."
    )
    p.add_argument("keywords", type=str, nargs="+", help="Search keywords")


class ArgumentParser(argparse.ArgumentParser):
    """Override default error method of all parsers to show help of subcommand"""

    def error(self, message):
        self.print_help()
        self.exit(2, "%s: error: %s\n" % (self.prog, message))


class AlbumParser(ArgumentParser):
    def __init__(self):
        super().__init__()
        self.parent_parser = self.create_parent_parser()
        self.parser = self.create_parser()
        self.subparsers = self.parser.add_subparsers(
            title="actions", help="sub-command help"
        )

    @staticmethod
    def create_parent_parser():
        """Parent parser for all subparsers to have the same set of arguments."""
        parent_parser = ArgumentParser(add_help=False)
        # parse logging
        parent_parser.add_argument(
            "--log",
            required=False,
            help="Logging level for your album command. Choose between %s"
            % ", ".join([loglevel.name for loglevel in LogLevel]),
            default=LogLevel(debug_settings()),
            type=(lambda choice: to_loglevel(choice)),
        )
        parent_parser.add_argument(
            "--json",
            required=False,
            help="Adding this parameter prevents the log from being printed to the console."
            " Instead, the result of the command - if present - is printed as JSON.",
            action="store_true",
        )
        parent_parser.add_argument(
            "--version", "-V", action="version", version="%s " % core.__version__
        )
        return parent_parser

    def create_parser(self):
        """Creates the main parser for the album framework."""
        parser = ArgumentParser(
            add_help=True,
            description="album for running, building, and deploying computational solutions",
            parents=[self.parent_parser],
        )
        return parser

    def create_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a album command, specified by a name, a function and a help description."""
        parser = self.subparsers.add_parser(
            command_name, help=command_help, parents=[self.parent_parser]
        )
        parser.set_defaults(func=command_function)
        return parser

    def create_file_command_parser(self, command_name, command_function, command_help):
        """Creates a parser for a album command dealing with an album file.

        Parser is specified by a name, a function and a help description.
        """
        parser = self.create_command_parser(
            command_name, command_function, command_help
        )
        parser.add_argument("path", type=str, help="path for the solution file")
        return parser


if __name__ == "__main__":
    main()
