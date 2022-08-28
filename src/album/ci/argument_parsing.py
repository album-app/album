import os
import sys
import traceback
from argparse import ArgumentParser

from album.api import Album
from album.argument_parsing import ArgumentParser as AlbumAP
from album.ci.commandline import (
    configure_repo,
    configure_ssh,
    zenodo_publish,
    zenodo_upload,
    update_index,
    commit_changes,
    merge,
)
from album.ci.controller.release_manager import ReleaseManager
from album.runner import album_logging
from album.runner.album_logging import (
    get_active_logger,
    debug_settings,
    pop_active_logger,
)

module_logger = get_active_logger


def main():
    """Entry points of `album ci`."""
    ci_parser = create_parser()

    module_logger().info("Starting CI release cycle...")
    args = ci_parser.parse_args()

    album_ci_command = ""
    try:
        album_ci_command = sys.argv[
            1
        ]  # album command always expected at second position
    except IndexError:
        ci_parser.error("Please provide a valid action!")

    pop_active_logger()  # there will be a new one with the album instance

    # Makes sure album is initialized.
    album_instance = create_album_instance()
    album_instance.load_or_create_collection()

    album_logging.set_loglevel(args.log)

    release_manager = ReleaseManager(
        album_instance, args.name, args.path, args.src, args.force_retrieve
    )
    module_logger().debug("Running %s command..." % album_ci_command)

    try:
        args.func(release_manager, args)  # execute entry point function
    except Exception as e:
        _handle_exception(e)
    finally:
        release_manager.close()


def _handle_exception(e):
    get_active_logger().error("album-ci command failed: %s" % str(e))
    get_active_logger().debug(traceback.format_exc())
    sys.exit(e)


def create_album_instance() -> Album:
    return Album.Builder().build()


def create_parser():
    parser = AlbumCIParser()

    parser.create_git_command_parser(
        "configure-repo",
        configure_repo,
        "Configures the git configuration for the catalog repository. Sets an name and an email.",
    )

    p = parser.create_catalog_command_parser(
        "configure-ssh",
        configure_ssh,
        "Configures the git push option for the catalog repository to use the ssh protocol instead of https. "
        "Needs the systems git configuration to be configured for ssh usage!",
    )
    p.add_argument(
        "--ci-project-path",
        required=False,
        type=str,
        help="The project path of the git repository."
        'E.g. for https://gitlab.com/album-app/album.git the project path is "album-app/album". '
        "Usually necessary for using album-ci from within a CI-pipeline."
        "Allows switching from https to ssh source."
        'Can be set via environment variable "CI_PROJECT_PATH".',
        default=os.getenv("CI_PROJECT_PATH", None),
    )

    parser.create_zenodo_command_parser(
        "publish",
        zenodo_publish,
        "Publishes the corresponding zenodo deposit of a catalog repository deployment branch.",
    )
    p = parser.create_zenodo_command_parser(
        "upload",
        zenodo_upload,
        "Uploads solution of a catalog repository deployment branch to zenodo."
        "Thereby only allowing a single solution per branch.",
    )
    p.add_argument(
        "--report-file",
        required=False,
        help="Path to a report file. If given, a report of the upload will be created.",
        default="",
        type=str,
    )

    p = parser.create_branch_command_parser(
        "update",
        update_index,
        "Updates the index of the catalog repository to include the solution of a catalog repository deployment branch.",
    )
    p.add_argument(
        "--doi",
        required=False,
        help="Sets the DOI of the solution. Overwrites DOI if already specified in the solution.",
        default="",
        type=str,
    )
    p.add_argument(
        "--deposit-id",
        required=False,
        help="Sets the zenodo deposit_id of the solution.",
        default="",
        type=str,
    )

    parser.create_branch_command_parser(
        "commit",
        commit_changes,
        "Pushes all changes to catalog repository deployment branch to the branch origin.",
    )

    parser.create_pipeline_command_parser(
        "merge", merge, "Merge the updated catalog index from the given branch to main."
    )

    return parser.parser


class AlbumCIParser(AlbumAP):
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
            help="Logging level for your album-ci command. Choose between %s"
            % ", ".join([loglevel.name for loglevel in album_logging.LogLevel]),
            default=album_logging.LogLevel(debug_settings()),
            type=(lambda choice: album_logging.to_loglevel(choice)),
        )
        return parent_parser

    def create_parser(self):
        """Creates the main parser for the album framework."""
        parser = ArgumentParser(
            add_help=True,
            description="album-catalog-admin for managing catalog-deploy requests to a catalog via commandline or CI",
            parents=[self.parent_parser],
        )
        return parser

    def create_catalog_command_parser(
        self, command_name, command_function, command_help
    ):
        """Creates a subparser with all necessary arguments for the catalog deployment management"""
        parser = self.subparsers.add_parser(
            command_name, help=command_help, parents=[self.parent_parser]
        )
        parser.set_defaults(func=command_function)
        parser.add_argument("name", type=str, help="Name of the catalog.")
        parser.add_argument(
            "path",
            type=str,
            help="Path of the catalog repository. Can be an empty folder.",
        )
        parser.add_argument(
            "src",
            type=str,
            help="Source of the catalog. Usually a git repository link.",
        )

        parser.add_argument(
            "--force-retrieve",
            required=False,
            help="If True, download path for the catalog will be force emptied before retrieving the catalog.",
            default=False,
            type=bool,
        )

        return parser

    def create_git_command_parser(self, command_name, command_function, command_help):
        parser = self.create_catalog_command_parser(
            command_name, command_function, command_help
        )
        parser.add_argument(
            "--ci-user-name",
            required=False,
            type=str,
            help="Name to use for all ci operations. "
            'Can be set via environment variable "CI_USER_NAME".'
            "If neither is given, system is required to be proper configured!",
            default=os.getenv("CI_USER_NAME", None),
        )
        parser.add_argument(
            "--ci-user-email",
            required=False,
            type=str,
            help="Email to use for all ci operations. "
            'Can be set via environment variable "CI_USER_EMAIL".'
            "If neither is given, system is required to be proper configured!",
            default=os.getenv("CI_USER_EMAIL", None),
        )

        return parser

    def create_branch_command_parser(
        self, command_name, command_function, command_help
    ):
        parser = self.create_git_command_parser(
            command_name, command_function, command_help
        )
        parser.add_argument(
            "--branch-name",
            required=True,
            type=str,
            help="The branch name of the solution to publish.",
        )
        return parser

    def create_zenodo_command_parser(
        self, command_name, command_function, command_help
    ):
        parser = self.create_branch_command_parser(
            command_name, command_function, command_help
        )
        parser.add_argument(
            "--zenodo-base-url",
            required=False,
            type=str,
            help='The base URL where to upload to. Either "https://sandbox.zenodo.org" or "https://zenodo.org"'
            'Can be set via environment variable "ZENODO_BASE_URL".',
            default=os.getenv("ZENODO_BASE_URL", None),
        )
        parser.add_argument(
            "--zenodo-access-token",
            required=False,
            type=str,
            help="The access token representing the zenodo user account to use. For help see zenodo.org!"
            'Can be set via environment variable "ZENODO_ACCESS_TOKEN".',
            default=os.getenv("ZENODO_ACCESS_TOKEN", None),
        )
        return parser

    def create_pipeline_command_parser(
        self, command_name, command_function, command_help
    ):
        parser = self.create_branch_command_parser(
            command_name, command_function, command_help
        )
        parser.add_argument(
            "--dry-run",
            required=False,
            help="Dry-run option."
            " If this argument is added, commits will not be pushed, only information is shown.",
            action="store_true",
        )
        parser.add_argument(
            "--push-option",
            required=False,
            help="Push options for the catalog repository.",
            default=None,
            nargs="+",
        )
        return parser
