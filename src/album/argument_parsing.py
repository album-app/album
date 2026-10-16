"""Argument parsing for the album command line interface."""

import argparse
import sys
import traceback
from importlib.metadata import entry_points

from album import core
from album.api import Album
from album.commandline import (
    add_catalog,
    clone,
    deploy,
    index,
    info,
    install,
    remove_catalog,
    repl,
    run,
    search,
    test,
    undeploy,
    uninstall,
    update,
    upgrade,
    upgrade_solutions,
)
from album.environments.utils.subcommand import SubProcessError
from album.runner.album_logging import (
    LogLevel,
    debug_settings,
    get_active_logger,
    to_loglevel,
)

# help of the positional solution argument of every command that resolves a solution
SOLUTION_HELP = (
    "the solution: [catalog:]group:name:version (or a shorter form such as group:name), "
    "a DOI, a URL, or the path to a solution file, folder or zip"
)


def main():
    """Entry points of `album`."""
    parser = create_parser()

    get_active_logger().debug("Parsing base album call arguments...")
    namespace, args = parser.parse_known_args()
    __handle_args(namespace, args, parser)


def __handle_args(namespace, args, parser):
    """Handle all arguments provided after the album command."""
    level = namespace.log
    print_json = getattr(namespace, "json", False)
    __run_subcommand(namespace, args, parser, level, print_json)


def _capture_output():
    """Capture the output of the logger to a file."""
    logger = get_active_logger()
    logger.handlers.clear()


def _handle_exception(e, silent: bool = False):
    """Handle exceptions and exits the program."""
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
    """Call a specific album subcommand."""
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
    """Create an album instance with a specific log level."""
    return Album.Builder().log_level(level).build()


def create_parser():
    """Create a parser for all known album arguments."""
    parser = AlbumParser()
    parser_creators = []
    for entry_point in entry_points(group="console_parsers_album"):
        try:
            parser_creators.append(entry_point.load())
        except Exception as e:
            get_active_logger().error(
                f"Cannot load console parser {entry_point.name}. Error: {str(e)}"
            )
            get_active_logger().debug(str(e))
    for parse_creator in parser_creators:
        parse_creator(parser)
    return parser.parser


def create_test_parser(parser):
    """Create a parser for the test command."""
    parser.create_file_command_parser(
        "test", test, "execute the test routine of a solution."
    )


def create_index_parser(parser):
    """Create a parser for the index command."""
    p = parser.create_command_parser(
        "index", index, "print the index of the local album collection."
    )
    p.add_argument(
        "--all",
        required=False,
        help="Show all versions of each solution, including outdated ones.",
        action="store_true",
    )


def create_clone_parser(parser):
    """Create a parser for the clone command."""
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
        help="The target directory where the solution or catalog will be added to. "
        "For a catalog, this can also be an empty GIT repository URL.",
    )
    p.add_argument(
        "name", type=str, help="The new name of the cloned solution or catalog."
    )


def create_upgrade_parser(parser):
    """Create a parser for the upgrade command."""
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


def create_upgrade_solutions_parser(parser):
    """Create a parser for the upgrade-solutions command."""
    p = parser.create_command_parser(
        "upgrade-solutions",
        upgrade_solutions,
        "install the latest version of installed solutions from their catalogs, and uninstall the "
        "versions it replaces once no other solution runs in them.",
    )
    p.add_argument(
        "solutions",
        nargs="*",
        metavar="solution",
        help="an installed solution to upgrade: [catalog:]group:name:version or a shorter form such "
        "as group:name. Without one, all installed solutions are upgraded. Solutions installed "
        "from a file, URL or DOI are not upgraded.",
    )
    p.add_argument(
        "--dry-run",
        required=False,
        help="Only show what would be installed and uninstalled.",
        action="store_true",
    )


def create_update_parser(parser):
    """Create a parser for the update command."""
    p = parser.create_command_parser(
        "update",
        update,
        "Update the catalog index files. Either all catalogs configured, or a specific one.",
    )
    p.add_argument("catalog", type=str, help="name of the catalog", nargs="?")


def create_remove_catalog_parser(parser):
    """Create a parser for the remove-catalog command."""
    p = parser.create_command_parser(
        "remove-catalog",
        remove_catalog,
        "remove a catalog from your local album configuration file.",
    )
    p.add_argument("name", type=str, help="name of the catalog")


def create_add_catalog_parser(parser):
    """Create a parser for the add-catalog command."""
    p = parser.create_command_parser(
        "add-catalog",
        add_catalog,
        "add a catalog to your local album configuration file.",
    )
    p.add_argument("src", type=str, help="src of the catalog")


def create_info_parser(parser):
    """Create a parser for the info command."""
    parser.create_file_command_parser(
        "info", info, "print information about an album solution."
    )


def create_uninstall_parser(parser):
    """Create a parser for the uninstall command."""
    p = parser.create_file_command_parser(
        "uninstall", uninstall, "uninstall an album solution."
    )
    p.add_argument(
        "--uninstall-deps",
        required=False,
        help="Also uninstall the parent solution, and its parents in turn. A parent that other "
        "installed solutions still depend on stays installed.",
        default=False,
        action="store_true",
    )


def create_install_parser(parser):
    """Create a parser for the install command."""
    p = parser.create_file_command_parser(
        "install", install, "install an album solution."
    )
    p.add_argument(
        "--allow-recursive",
        required=False,
        help="Install even if the solution environment requires a different album version (album in album). "
        "Both albums then share the base path and collection database unless configured otherwise, "
        "which can break the database or the solution's runner. The same or an unpinned album version "
        "is always accepted, with a warning.",
        action="store_true",
    )
    p.add_argument(
        "--reinstall",
        required=False,
        help="Install the solution again if it is installed, e.g. after it was deployed again with the "
        "same version. It is installed from its catalog, or from the file, URL or DOI given; a solution "
        "installed from a file, URL or DOI and given by group:name:version is installed from its copy "
        "in album. The solutions running in its environment are installed again with it if they come "
        "from a catalog. If one of them was installed from a file, URL or DOI, nothing is changed: "
        "album leaves the environment of such a solution untouched. Everything is downloaded before "
        "anything is uninstalled.",
        action="store_true",
    )


def create_deploy_parser(parser):
    """Create a parser for the deploy command."""
    p = parser.create_file_command_parser(
        "deploy",
        deploy,
        "deploy an album solution.",
        path_help="path to the solution file, or to the folder that holds solution.py and its other files",
        path_metavar="path",
    )
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
        help="When specified, force deploys a solution to a catalog."
        " Useful if the solution has already been deployed once.",
        action="store_true",
    )
    p.add_argument(
        "--changelog",
        required=False,
        help="Description of changes from the previous version of the solution to this version.",
        default=None,
    )

    p.add_argument(
        "--no-conda-lock",
        required=False,
        help="When specified, the conda.lock file will not be created.",
        action="store_true",
    )


def create_undeploy_parser(parser):
    """Create a parser for the undeploy command."""
    p = parser.create_file_command_parser(
        "undeploy",
        undeploy,
        "undeploy an album solution.",
        path_help="group:name:version of the solution to remove from the catalog",
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
    """Create a parser for the repl command."""
    parser.create_file_command_parser(
        "repl", repl, "get an interactive repl for an album solution."
    )


def create_run_parser(parser):
    """Create a parser for the run command."""
    p = parser.create_file_command_parser("run", run, "run an album solution.")
    p.add_argument(
        "--install",
        required=False,
        help="Install the solution first if it is not installed.",
        action="store_true",
    )


def create_search_parser(parser):
    """Create a parser for the search command."""
    p = parser.create_command_parser(
        "search", search, "search for an album solution using keywords."
    )
    p.add_argument("keywords", type=str, nargs="+", help="Search keywords")


class ArgumentParser(argparse.ArgumentParser):
    """Parser of album and its commands, the base of every album parser.

    Long options are only matched in full. album passes every argument it does not know on to
    the solution, so a solution argument such as --js must not be taken for album's --json.
    """

    def __init__(self, *args, **kwargs):
        """Create the parser. Abbreviated long options are not recognized."""
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def error(self, message):
        """Override default error method of all parsers to show help of subcommand."""
        self.print_help()
        self.exit(2, f"{self.prog}: error: {message}\n")


class AlbumParser(ArgumentParser):
    """Parser for the album command line interface."""

    def __init__(self):
        """Initialize the album parser."""
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
        """Create the main parser for the album framework."""
        parser = ArgumentParser(
            add_help=True,
            description="album for running, building, and deploying computational solutions",
            parents=[self.parent_parser],
        )
        return parser

    def create_command_parser(self, command_name, command_function, command_help):
        """Create a parser for a album command, specified by a name, a function and a help description."""
        parser = self.subparsers.add_parser(
            command_name, help=command_help, parents=[self.parent_parser]
        )
        parser.set_defaults(func=command_function)
        return parser

    def create_file_command_parser(
        self,
        command_name,
        command_function,
        command_help,
        path_help=SOLUTION_HELP,
        path_metavar="solution",
    ):
        """Create a parser for a album command dealing with a solution.

        Parser is specified by a name, a function and a help description. The solution is
        the positional argument "path", its help and its name in the usage can be set.
        """
        parser = self.create_command_parser(
            command_name, command_function, command_help
        )
        parser.add_argument("path", type=str, metavar=path_metavar, help=path_help)
        return parser


if __name__ == "__main__":
    main()
