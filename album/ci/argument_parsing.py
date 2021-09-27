import os
import sys
from argparse import ArgumentParser

from album.argument_parsing import ArgumentParser as AlbumAP
from album.ci.commandline import configure_repo, configure_ssh, zenodo_publish, zenodo_upload, update_index, \
    push_changes
from album_runner import logging
from album_runner.logging import get_active_logger, debug_settings

module_logger = get_active_logger


def main():
    """Entry points of `album ci`."""
    ci_parser = create_parser()

    module_logger().info("Starting CI release cycle...")
    args = ci_parser.parse_known_args()

    logging.set_loglevel(args[0].log)

    album_ci_command = ""
    try:
        album_ci_command = sys.argv[1]  # album command always expected at second position
    except IndexError:
        ci_parser.error("Please provide a valid action!")
    module_logger().debug("Running %s command..." % album_ci_command)
    sys.argv = [sys.argv[0]] + args[1]
    args[0].func(args[0])  # execute entry point function


def create_parser():
    parser = AlbumCIParser()

    parser.create_git_command_parser(
        'configure-repo',
        configure_repo,
        'Configures the git configuration for the catalog repository. Sets an name and an email.'
    )

    p = parser.create_catalog_command_parser(
        'configure-ssh',
        configure_ssh,
        'Configures the git push option for the catalog repository to use the ssh protocol instead of https. '
        'Needs the systems git configuration to be configured for ssh usage!'
    )
    p.add_argument(
        '--ci_project_path',
        required=False,
        type=str,
        help='The project path of the git repository.'
             'E.g. for https://gitlab.com/album-app/album.git the project path is \"album-app/album\". '
             'Usually necessary for using album-ci from within a CI-pipeline.'
             'Allows switching from https to ssh source.'
             'Can be set via environment variable \"CI_PROJECT_PATH\".',
        default=os.getenv('CI_PROJECT_PATH', None)
    )

    p = parser.create_zenodo_command_parser(
        'publish',
        zenodo_publish,
        'Publishes the corresponding zenodo deposit of a catalog repository deployment branch.'
    )
    p = parser.create_zenodo_command_parser(
        'upload',
        zenodo_upload,
        'Uploads solution of a catalog repository deployment branch to zenodo.'
        'Thereby only allowing a single solution per branch.'
    )

    p = parser.create_branch_command_parser(
        'update',
        update_index,
        'Updates the index of the catalog repository to include the solution of a catalog repository deployment branch.'
    )

    p = parser.create_branch_command_parser(
        'push',
        push_changes,
        'Pushes all changes to catalog repository deployment branch to the branch origin.'
    )
    p.add_argument(
        '--dry-run',
        required=False,
        help='Dry-run option. If this argument is added, no merge request will be created, only information is shown.',
        action='store_true'
    )
    p.add_argument(
        '--trigger-pipeline',
        required=False,
        help='Trigger-CI-pipeline option. If True will trigger CI pipeline. '
             'If program call is configured as CI pipeline itself, make sure call is not re-triggered!'
             'Default False. Choose between %s' %
             ", ".join([str(True), str(False)]),
        default=False,
        type=(lambda choice: bool(choice)),
    )

    return parser.parser


class AlbumCIParser(AlbumAP):
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
            help='Logging level for your album-ci command. Choose between %s' %
                 ", ".join([loglevel.name for loglevel in logging.LogLevel]),
            default=logging.LogLevel(debug_settings()),
            type=(lambda choice: logging.to_loglevel(choice)),
        )
        return parent_parser

    def create_parser(self):
        """Creates the main parser for the hip framework."""
        parser = ArgumentParser(
            add_help=True,
            description=
            'album-catalog-admin for managing catalog-deploy requests to a catalog via commandline or CI',
            parents=[self.parent_parser])
        return parser

    def create_catalog_command_parser(self, command_name, command_function, command_help):
        """Creates a subparser with all necessary arguments for the catalog deployment management"""
        parser = self.subparsers.add_parser(command_name, help=command_help, parents=[self.parent_parser])
        parser.set_defaults(func=command_function)
        parser.add_argument('name', type=str, help='Name of the catalog.')
        parser.add_argument('path', type=str, help='Path of the catalog repository. Can be an empty folder.')
        parser.add_argument('src', type=str, help='Source of the catalog. Usually a git repository link.')

        parser.add_argument(
            '--force_retrieve',
            required=False,
            help='If True, download path for the catalog will emptied before retrieving the catalog.',
            default=True,
            type=bool,
        )

        return parser

    def create_git_command_parser(self, command_name, command_function, command_help):
        parser = self.create_catalog_command_parser(command_name, command_function, command_help)
        parser.add_argument(
            '--ci_user_name',
            required=False,
            type=str,
            help='Name to use for all ci operations. '
                 'Can be set via environment variable \"CI_USER_NAME\".'
                 'If neither is given, system is required to be proper configured!',
            default=os.getenv('CI_USER_NAME', None)
        )
        parser.add_argument(
            '--ci_user_email',
            required=False,
            type=str,
            help='Email to use for all ci operations. '
                 'Can be set via environment variable \"CI_USER_EMAIL\".'
                 'If neither is given, system is required to be proper configured!',
            default=os.getenv('CI_USER_EMAIL', None)
        )

        return parser

    def create_branch_command_parser(self, command_name, command_function, command_help):
        parser = self.create_git_command_parser(command_name, command_function, command_help)
        parser.add_argument(
            '--branch_name',
            required=True,
            type=str,
            help='The branch name of the solution to publish.'
        )
        return parser

    def create_zenodo_command_parser(self, command_name, command_function, command_help):
        parser = self.create_branch_command_parser(command_name, command_function, command_help)
        parser.add_argument(
            '--zenodo-base-url',
            required=False,
            type=str,
            help='The base URL where to upload to. Either \"sandbox.zenodo.org\" or \"zenodo.org\"'
                 'Can be set via environment variable \"ZENODO_BASE_URL\".',
            default=os.getenv('ZENODO_BASE_URL', None)
        )
        parser.add_argument(
            '--zenodo-access-token',
            required=False,
            type=str,
            help='The access token representing the zenodo user account to use. For help see zenodo.org!'
                 'Can be set via environment variable \"ZENODO_ACCESS_TOKEN\".',
            default=os.getenv('ZENODO_ACCESS_TOKEN', None)
        )

        return parser
