from pathlib import Path

from album.ci.controller.zenodo_manager import ZenodoManager
from album.ci.utils.ci_utils import get_ssh_url
from album.core.concept.singleton import Singleton
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.model.group_name_version import GroupNameVersion
from album.core.utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml, get_dict_entry
from album.core.utils.operations.git_operations import checkout_branch, add_files_commit_and_push, \
    retrieve_single_file_from_head, configure_git
from album.core.utils.operations.resolve_operations import get_zip_name, get_zip_name_prefix, dict_to_group_name_version
from album_runner import logging

module_logger = logging.get_active_logger


class ReleaseManager(metaclass=Singleton):

    def __init__(self, catalog_name, catalog_path, catalog_src):
        self.catalog_name = catalog_name
        self.catalog_path = catalog_path
        self.catalog_src = catalog_src

        self.catalog = Catalog(None, name=self.catalog_name, path=catalog_path, src=self.catalog_src)
        self.catalog_repo = self.catalog.retrieve_catalog(force_retrieve=True)
        self.catalog.load_index()

    def configure_repo(self, user_name, user_email):
        configure_git(self.catalog_repo, user_email, user_name)

    def configure_ssh(self, project_path):
        if not project_path:
            raise KeyError("Project path not given!")

        if not self.catalog_repo.remote().url.startswith("git"):
            self.catalog_repo.remote().set_url(get_ssh_url(project_path, self.catalog_src))

    @staticmethod
    def _get_zip_path(group_name_version: GroupNameVersion):
        zip_name = get_zip_name(group_name_version)
        return Path("").joinpath(DefaultValues.cache_path_solution_prefix.value, group_name_version.group,
                                 group_name_version.name, group_name_version.version, zip_name)

    @staticmethod
    def _get_yml_dict(head):
        yml_file_path = retrieve_single_file_from_head(head, DefaultValues.catalog_yaml_prefix.value)
        yml_dict = get_dict_from_yml(yml_file_path)

        return [yml_dict, yml_file_path]

    def zenodo_publish(self, branch_name, zenodo_base_url, zenodo_access_token):
        zenodo_manager = ZenodoManager(zenodo_base_url, zenodo_access_token)

        head = checkout_branch(self.catalog_repo, branch_name)

        # get the yml file to release from current branch
        yml_dict, yml_file_path = self._get_yml_dict(head)

        # retrieve the deposit from zenodo by id
        zip_path = self._get_zip_path(dict_to_group_name_version(yml_dict))
        deposit_name = get_zip_name_prefix(dict_to_group_name_version(yml_dict))
        deposit_id = get_dict_entry(yml_dict, "deposit_id", allow_none=False)
        deposit = zenodo_manager.zenodo_get_unpublished_deposit_by_id(
            deposit_name, deposit_id, expected_files=[zip_path]
        )

        # publish to zenodo
        deposit.publish()

    def zenodo_upload(self, branch_name, zenodo_base_url, zenodo_access_token):
        zenodo_manager = ZenodoManager(zenodo_base_url, zenodo_access_token)

        head = checkout_branch(self.catalog_repo, branch_name)

        # get the yml file to release
        yml_dict, yml_file_path = self._get_yml_dict(head)

        # get metadata from yml_file
        try:
            deposit_id = yml_dict["deposit_id"]
        except KeyError:
            deposit_id = None

        # extract deposit name
        deposit_name = get_zip_name_prefix(dict_to_group_name_version(yml_dict))

        # get the solution zip to release
        zip_path = self._get_zip_path(dict_to_group_name_version(yml_dict))
        solution_zip = retrieve_single_file_from_head(head, str(zip_path))

        # get the release deposit. Either a new one or an existing one to perform an update on
        deposit = zenodo_manager.zenodo_get_deposit(deposit_name, deposit_id, expected_files=[solution_zip])

        # include doi and ID in yml
        yml_dict["doi"] = deposit.metadata.prereserve_doi["doi"]
        yml_dict["deposit_id"] = deposit.id
        write_dict_to_yml(yml_file_path, yml_dict)

        # zenodo upload solution but not publish
        zenodo_manager.zenodo_upload(deposit, solution_zip)

    def update_index(self, branch_name):
        head = checkout_branch(self.catalog_repo, branch_name)

        yml_dict, _ = self._get_yml_dict(head)

        self.catalog.catalog_index.update(yml_dict)
        self.catalog.catalog_index.save()
        self.catalog.catalog_index.export(self.catalog.solution_list_path)

    def push_changes(self, branch_name, dry_run, trigger_pipeline, ci_user_name, ci_user_email):
        head = checkout_branch(self.catalog_repo, branch_name)

        yml_dict, yml_file_path = self._get_yml_dict(head)

        zip_path = self._get_zip_path(dict_to_group_name_version(yml_dict))
        solution_zip = retrieve_single_file_from_head(head, str(zip_path))

        commit_files = [yml_file_path, solution_zip, self.catalog.index_path, self.catalog.solution_list_path]
        if not all([Path(f).is_file() for f in commit_files]):
            raise FileNotFoundError("Invalid deploy request or broken catalog repository!")

        commit_msg = "CI updated %s" % branch_name
        add_files_commit_and_push(
            head,
            commit_files,
            commit_msg,
            push=not dry_run,
            trigger_pipeline=trigger_pipeline,
            username=ci_user_name,
            email=ci_user_email
        )

        return True
