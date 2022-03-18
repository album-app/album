from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

from git import Repo

from album.api import Album
from album.ci.controller.zenodo_manager import ZenodoManager
from album.ci.utils.continuous_integration import get_ssh_url, create_report
from album.core.model.catalog import Catalog, retrieve_index_files_from_src
from album.core.utils.export.changelog import get_changelog_file_name
from album.core.utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml, get_dict_entry, \
    copy, force_remove
from album.core.utils.operations.git_operations import checkout_branch, add_files_commit_and_push, \
    retrieve_files_from_head, configure_git
from album.core.utils.operations.resolve_operations import get_zip_name, get_zip_name_prefix, dict_to_coordinates
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class ReleaseManager:
    """Class for handling a catalog as administrator."""

    configuration = None

    def __init__(self, album_instance: Album, catalog_name, catalog_path, catalog_src, force_retrieve):
        self.catalog_name = catalog_name
        self.catalog_path = catalog_path
        self.catalog_src = catalog_src

        self.configuration = album_instance.configuration()
        if not self.configuration.is_setup():
            self.configuration.setup()

        self.catalog = Catalog(None, name=self.catalog_name, path=catalog_path, src=self.catalog_src)
        self.force_retrieve = force_retrieve
        self.album_instance = album_instance

    def _open_repo(self) -> Generator[Repo, None, None]:
        repo = self.catalog.retrieve_catalog(force_retrieve=self.force_retrieve, update=False)

        return repo

    def close(self):
        if self.catalog:
            self.catalog.dispose()

    def configure_repo(self, user_name, user_email):
        module_logger().info("Configuring repository using:\n\tusername:\t%s\n\temail:\t%s" % (user_name, user_email))
        with self._open_repo() as repo:
            configure_git(repo, user_email, user_name)

    def configure_ssh(self, project_path):
        module_logger().info("Configure ssh protocol for repository %s" % project_path)
        with self._open_repo() as repo:
            if not repo.remote().url.startswith("git"):
                repo.remote().set_url(get_ssh_url(project_path, self.catalog_src))

    def _get_zip_path(self, coordinates: ICoordinates):
        zip_name = get_zip_name(coordinates)
        return self.configuration.get_solution_path_suffix(coordinates).joinpath(zip_name)

    def _get_docker_path(self, coordinates: ICoordinates):
        docker_name = "Dockerfile"
        return self.configuration.get_solution_path_suffix(coordinates).joinpath(docker_name)

    def _get_changelog_path(self, coordinates: ICoordinates):
        changelog_name = get_changelog_file_name()
        return self.configuration.get_solution_path_suffix(coordinates).joinpath(changelog_name)

    def _get_documentation_paths(self, coordinates: ICoordinates, yml_dict: dict):
        solution_path_suffix = self.configuration.get_solution_path_suffix(coordinates)
        documentation_paths = []
        if "documentation" in yml_dict.keys():
            documentation_list = yml_dict["documentation"]
            if not isinstance(documentation_list, list):
                documentation_list = [documentation_list]

            for documentation_name in documentation_list:
                documentation_paths.append(solution_path_suffix.joinpath(documentation_name))
        return documentation_paths

    @staticmethod
    def _get_yml_dict(head):
        yml_file_path = retrieve_files_from_head(head, '[a-zA-Z0-9]*.yml')[0]
        yml_dict = get_dict_from_yml(yml_file_path)

        return [yml_dict, yml_file_path]

    def zenodo_publish(self, branch_name, zenodo_base_url, zenodo_access_token):
        zenodo_base_url, zenodo_access_token = self.__prepare_zenodo_arguments(zenodo_base_url, zenodo_access_token)

        zenodo_manager = self._get_zenodo_manager(zenodo_access_token, zenodo_base_url)

        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            # get the yml file to release from current branch
            yml_dict, yml_file_path = self._get_yml_dict(head)

        # checkout files
        zip_name = self._get_zip_path(dict_to_coordinates(yml_dict)).name
        docker_name = self._get_docker_path(dict_to_coordinates(yml_dict)).name

        # query deposit
        deposit_name = get_zip_name_prefix(dict_to_coordinates(yml_dict))
        deposit_id = get_dict_entry(yml_dict, "deposit_id", allow_none=False)

        module_logger().info("Get unpublished deposit with deposit id %s..." % deposit_id)
        deposit = zenodo_manager.zenodo_get_unpublished_deposit_by_id(
            deposit_id, deposit_name, expected_files=[zip_name, docker_name]
        )

        # publish to zenodo
        deposit.publish()
        module_logger().info("Published unpublished deposit with deposit id %s..." % deposit_id)

    def zenodo_upload(self, branch_name, zenodo_base_url, zenodo_access_token, report_file):
        zenodo_base_url, zenodo_access_token = self.__prepare_zenodo_arguments(zenodo_base_url, zenodo_access_token)

        zenodo_manager = self._get_zenodo_manager(zenodo_access_token, zenodo_base_url)
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            # get the yml file to release
            yml_dict, yml_file_path = self._get_yml_dict(head)

        # get metadata from yml_file
        try:
            deposit_id = yml_dict["deposit_id"]
        except KeyError:
            deposit_id = None
        coordinates = dict_to_coordinates(yml_dict)

        # do not upload SNAPSHOT versions
        if coordinates.version().endswith("SNAPSHOT"):
            module_logger().info("Will not upload SNAPSHOT version to zenodo! Skipping...")
            return

        # extract deposit name
        deposit_name = get_zip_name_prefix(coordinates)

        # get the solution zip to release
        zip_path = self._get_zip_path(dict_to_coordinates(yml_dict))
        solution_zip = retrieve_files_from_head(head, str(zip_path), option="startswith")[0]

        # get the docker file
        docker_path = self._get_docker_path(dict_to_coordinates(yml_dict))
        docker_file = retrieve_files_from_head(head, str(docker_path), option="startswith")[0]

        # get the changelog file
        changelog_path = self._get_changelog_path(dict_to_coordinates(yml_dict))
        changelog_file = retrieve_files_from_head(head, str(changelog_path), option="startswith")[0]

        # get the documentation files (if any)
        documentation_paths = self._get_documentation_paths(dict_to_coordinates(yml_dict), yml_dict)
        documentation_files = [
            retrieve_files_from_head(head, str(documentation_path), option="startswith")[0]
            for documentation_path in documentation_paths
        ]

        # get the release deposit. Either a new one or an existing one to perform an update on
        deposit = zenodo_manager.zenodo_get_deposit(
            deposit_name, deposit_id, expected_files=[solution_zip, docker_file, changelog_file]
        )
        module_logger().info("Deposit %s successfully retrieved..." % deposit.id)

        # include doi and ID in yml
        yml_dict["doi"] = deposit.metadata.prereserve_doi["doi"]
        yml_dict["deposit_id"] = deposit.id
        write_dict_to_yml(yml_file_path, yml_dict)

        # zenodo upload files but not publish
        deposit = zenodo_manager.zenodo_upload(deposit, solution_zip)
        zenodo_manager.zenodo_upload(deposit, docker_file)
        zenodo_manager.zenodo_upload(deposit, changelog_file)
        for documentation_file in documentation_files:
            zenodo_manager.zenodo_upload(deposit, documentation_file)
        module_logger().info("Deposit %s successfully retrieved..." % deposit_id)

        if report_file:
            report_file = create_report(report_file, {"DOI": yml_dict["doi"], "DEPOSIT_ID": yml_dict["deposit_id"]})
            module_logger().info("Created report file under %s" % str(report_file))

    @staticmethod
    def __prepare_zenodo_arguments(zenodo_base_url: str, zenodo_access_token: str):
        if zenodo_base_url is None or zenodo_access_token is None:
            raise RuntimeError('Zenodo base URL or Zenodo access token invalid! '
                               'See https://zenodo.org/ documentation for information!')

        zenodo_base_url = zenodo_base_url.strip()
        zenodo_access_token = zenodo_access_token.strip()

        if zenodo_base_url == "" or zenodo_access_token == "":
            raise RuntimeError("Empty zenodo base_url or zenodo_access_token!")

        module_logger().info("Using zenodo URL: %s" % zenodo_base_url)

        return zenodo_base_url, zenodo_access_token

    def update_index(self, branch_name, doi, deposit_id):
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            # always use remote index
            with TemporaryDirectory(dir=self.configuration.tmp_path()) as tmp_dir:
                repo = Path(tmp_dir).joinpath('repo')
                try:
                    index_db, index_meta = retrieve_index_files_from_src(self.catalog_src, branch_name=self.catalog.branch_name(), tmp_dir=repo)
                    if index_db.exists():
                        copy(index_db, self.catalog.index_file_path())
                    else:
                        module_logger().warning("Index not downloadable! Using Index in merge request branch!")
                finally:
                    force_remove(repo)

            self.album_instance.load_catalog_index(self.catalog)

            yml_dict, yml_file_path = self._get_yml_dict(head)

            # update doi and deposit_id if given
            log_message_doi = "without a doi"
            if doi:
                yml_dict["doi"] = doi
                log_message_doi = "with doi %s" % doi

            log_message_deposit = "without deposit"
            if deposit_id:
                yml_dict["deposit_id"] = deposit_id
                log_message_deposit = "in zenodo deposit %s" % deposit_id

            if doi or deposit_id:
                write_dict_to_yml(yml_file_path, yml_dict)

        module_logger().info(
            "Update index to include solution from branch %s %s %s!" %
            (branch_name, log_message_doi, log_message_deposit)
        )

        self.catalog.index().update(dict_to_coordinates(yml_dict), yml_dict)
        self.catalog.index().save()
        self.catalog.index().export(self.catalog.solution_list_path())

    def commit_changes(self, branch_name, ci_user_name, ci_user_email):
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            yml_dict, yml_file = self._get_yml_dict(head)

            # get the solution zip to release
            zip_path = self._get_zip_path(dict_to_coordinates(yml_dict))
            solution_zip = retrieve_files_from_head(head, str(zip_path), option="startswith")[0]

            # get the docker file
            docker_path = self._get_docker_path(dict_to_coordinates(yml_dict))
            docker_file = retrieve_files_from_head(head, str(docker_path), option="startswith")[0]

            # get the changelog file
            changelog_path = self._get_changelog_path(dict_to_coordinates(yml_dict))
            changelog_file = retrieve_files_from_head(head, str(changelog_path), option="startswith")[0]

            # get the documentation files (if any)
            documentation_paths = self._get_documentation_paths(dict_to_coordinates(yml_dict), yml_dict)
            documentation_files = [
                retrieve_files_from_head(head, str(documentation_path), option="startswith")[0]
                for documentation_path in documentation_paths
            ]

            commit_files = [yml_file, solution_zip, docker_file, changelog_file] + documentation_files
            if not all([Path(f).is_file() for f in commit_files]):
                raise FileNotFoundError("Invalid deploy request or broken catalog repository!")

            commit_msg = "Prepared branch \"%s\" for merging." % branch_name

            add_files_commit_and_push(
                head,
                commit_files,
                commit_msg,
                push=False,
                username=ci_user_name,
                email=ci_user_email
            )

        return True

    def merge(self, branch_name, dry_run, push_option, ci_user_name, ci_user_email):
        with self._open_repo() as repo:
            head = checkout_branch(repo, branch_name)

            commit_files = [
                self.catalog.solution_list_path(), self.catalog.index_file_path()
            ]
            if not all([Path(f).is_file() for f in commit_files]):
                raise FileNotFoundError("Invalid deploy request or broken catalog repository!")

            commit_msg = "Updated index."

            module_logger().info("Prepare merging...")

            add_files_commit_and_push(
                head,
                commit_files,
                commit_msg,
                push=not dry_run,
                push_option_list=push_option,
                username=ci_user_name,
                email=ci_user_email
            )

    def _get_zenodo_manager(self, zenodo_access_token, zenodo_base_url):
        # TODO in case one wants to reuse the zenodo manager, this needs to be smarter, but be aware that another call
        #  to this method might have different parameters
        return ZenodoManager(zenodo_base_url, zenodo_access_token)
