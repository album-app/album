from pathlib import Path

from git import Repo

from album.ci.controller.zenodo_manager import ZenodoManager
from album.ci.utils.ci_utils import get_ssh_url
from album.core.api.album import IAlbum
from album.core.model.catalog import Catalog
from album.core.utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml, get_dict_entry
from album.core.utils.operations.git_operations import checkout_branch, add_files_commit_and_push, \
    retrieve_single_file_from_head, configure_git
from album.core.utils.operations.resolve_operations import get_zip_name, get_zip_name_prefix, dict_to_coordinates
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class ReleaseManager:
    """Class for handling a catalog as administrator."""

    configuration = None

    def __init__(self, album_instance: IAlbum, catalog_name, catalog_path, catalog_src, force_retrieve):
        self.catalog_name = catalog_name
        self.catalog_path = catalog_path
        self.catalog_src = catalog_src

        self.configuration = album_instance.configuration()
        if not self.configuration.is_setup():
            self.configuration.setup()

        self.catalog = Catalog(None, name=self.catalog_name, path=catalog_path, src=self.catalog_src)
        self.catalog_repo: Repo = self.catalog.retrieve_catalog(force_retrieve=force_retrieve, update=False)
        album_instance.migration_manager().load_index(self.catalog)

    def __del__(self):
        if self.catalog:
            self.catalog.dispose()
        if self.catalog_repo:
            self.catalog_repo.close()

    def configure_repo(self, user_name, user_email):
        module_logger().info("Configuring repository using:\n\tusername:\t%s\n\temail:\t%s" % (user_name, user_email))
        configure_git(self.catalog_repo, user_email, user_name)

    def configure_ssh(self, project_path):
        if not project_path:
            raise KeyError("Project path not given!")

        if not self.catalog_repo.remote().url.startswith("git"):
            self.catalog_repo.remote().set_url(get_ssh_url(project_path, self.catalog_src))

    def _get_zip_path(self, coordinates: ICoordinates):
        zip_name = get_zip_name(coordinates)
        return self.configuration.get_solution_path_suffix(coordinates).joinpath(zip_name)

    def _get_docker_path(self, coordinates: ICoordinates):
        docker_name = "Dockerfile"
        return self.configuration.get_solution_path_suffix(coordinates).joinpath(docker_name)

    @staticmethod
    def _get_yml_dict(head):
        yml_file_path = retrieve_single_file_from_head(head, '[a-zA-Z0-9]*.yml')
        yml_dict = get_dict_from_yml(yml_file_path)

        return [yml_dict, yml_file_path]

    def zenodo_publish(self, branch_name, zenodo_base_url, zenodo_access_token):
        zenodo_base_url, zenodo_access_token = self.__prepare_zenodo_arguments(zenodo_base_url, zenodo_access_token)

        zenodo_manager = self._get_zenodo_manager(zenodo_access_token, zenodo_base_url)

        head = checkout_branch(self.catalog_repo, branch_name)

        # get the yml file to release from current branch
        yml_dict, yml_file_path = self._get_yml_dict(head)

        # checkout files
        zip_name = self._get_zip_path(dict_to_coordinates(yml_dict)).name
        docker_name = self._get_docker_path(dict_to_coordinates(yml_dict)).name

        # query deposit
        deposit_name = get_zip_name_prefix(dict_to_coordinates(yml_dict))
        deposit_id = get_dict_entry(yml_dict, "deposit_id", allow_none=False)
        deposit = zenodo_manager.zenodo_get_unpublished_deposit_by_id(
            deposit_id, deposit_name, expected_files=[zip_name, docker_name]
        )

        # publish to zenodo
        deposit.publish()

    def zenodo_upload(self, branch_name, zenodo_base_url, zenodo_access_token):
        zenodo_base_url, zenodo_access_token = self.__prepare_zenodo_arguments(zenodo_base_url, zenodo_access_token)

        zenodo_manager = self._get_zenodo_manager(zenodo_access_token, zenodo_base_url)

        head = checkout_branch(self.catalog_repo, branch_name)

        # get the yml file to release
        yml_dict, yml_file_path = self._get_yml_dict(head)

        # get metadata from yml_file
        try:
            deposit_id = yml_dict["deposit_id"]
        except KeyError:
            deposit_id = None

        # extract deposit name
        deposit_name = get_zip_name_prefix(dict_to_coordinates(yml_dict))

        # get the solution zip to release
        zip_path = self._get_zip_path(dict_to_coordinates(yml_dict))
        solution_zip = retrieve_single_file_from_head(head, str(zip_path), option="startswith")

        # get the docker file
        docker_path = self._get_docker_path(dict_to_coordinates(yml_dict))
        docker_file = retrieve_single_file_from_head(head, docker_path, option="startswith")

        # get the release deposit. Either a new one or an existing one to perform an update on
        deposit = zenodo_manager.zenodo_get_deposit(deposit_name, deposit_id, expected_files=[solution_zip])

        # include doi and ID in yml
        yml_dict["doi"] = deposit.metadata.prereserve_doi["doi"]
        yml_dict["deposit_id"] = deposit.id
        write_dict_to_yml(yml_file_path, yml_dict)

        # zenodo upload solution but not publish
        deposit = zenodo_manager.zenodo_upload(deposit, solution_zip)
        zenodo_manager.zenodo_upload(deposit, docker_file)

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

    def update_index(self, branch_name):
        head = checkout_branch(self.catalog_repo, branch_name)

        yml_dict, _ = self._get_yml_dict(head)

        self.catalog.index().update(dict_to_coordinates(yml_dict), yml_dict)
        self.catalog.index().save()
        self.catalog.index().export(self.catalog.solution_list_path())

    def push_changes(self, branch_name, dry_run, push_option, ci_user_name, ci_user_email):
        head = checkout_branch(self.catalog_repo, branch_name)

        yml_dict, yml_file = self._get_yml_dict(head)

        zip_path = self._get_zip_path(dict_to_coordinates(yml_dict))
        solution_zip = retrieve_single_file_from_head(head, str(zip_path), option="startswith")

        docker_path = self._get_docker_path(dict_to_coordinates(yml_dict))
        docker_file = retrieve_single_file_from_head(head, str(docker_path), option="startswith")

        commit_files = [
            yml_file, solution_zip, docker_file
        ]
        if not all([Path(f).is_file() for f in commit_files]):
            raise FileNotFoundError("Invalid deploy request or broken catalog repository!")

        commit_msg = "Prepared branch \"%s\" for merging." % branch_name

        add_files_commit_and_push(
            head,
            commit_files,
            commit_msg,
            push=not dry_run,
            push_options=push_option,
            username=ci_user_name,
            email=ci_user_email
        )

        return True

    def merge(self, branch_name, dry_run, push_option, ci_user_name, ci_user_email):
        head = checkout_branch(self.catalog_repo, branch_name)

        commit_files = [
            self.catalog.solution_list_path(), self.catalog.index_path()
        ]
        if not all([Path(f).is_file() for f in commit_files]):
            raise FileNotFoundError("Invalid deploy request or broken catalog repository!")

        commit_msg = "Updated index."

        add_files_commit_and_push(
            head,
            commit_files,
            commit_msg,
            push=not dry_run,
            push_options=push_option,
            username=ci_user_name,
            email=ci_user_email
        )

    def _get_zenodo_manager(self, zenodo_access_token, zenodo_base_url):
        # TODO in case one wants to reuse the zenodo manager, this needs to be smarter, but be aware that another call
        #  to this method might have different parameters
        return ZenodoManager(zenodo_base_url, zenodo_access_token)
