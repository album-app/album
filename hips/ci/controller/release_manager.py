from hips.ci.utils.ci_utils import get_ssh_url, retrieve_yml_file_path, retrieve_solution_file_path, \
    zenodo_get_deposit, \
    zenodo_upload
from hips.ci.utils.deploy_environment import get_ci_deploy_values, get_ci_git_config_values, get_ci_project_values
from hips.core import load
from hips.core.concept.singleton import Singleton
from hips.core.model.catalog import Catalog
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import get_dict_from_yml, set_zenodo_metadata_in_solutionfile, \
    write_dict_to_yml, get_yml_entry
from hips.core.utils.operations.git_operations import checkout_branch, add_files_commit_and_push
from hips_runner import logging

module_logger = logging.get_active_logger


class ReleaseManager(metaclass=Singleton):
    """Class handling a CI release.

    When a deploy routine creates a merge request to a catalog, the solution is uploaded to zenodo. This class handles
    the routine to do so.

    Requires the CI runner to be configured in a certain way - see deploy_environment

    """

    def __init__(self):
        branch_name, catalog_name, target_url, source_url = get_ci_deploy_values()
        user_name, user_email = get_ci_git_config_values()
        project_path, server_url = get_ci_project_values()

        self.project_path = project_path
        self.server_url = server_url

        self.branch_name = branch_name
        self.catalog_name = catalog_name
        self.target_url = target_url
        self.source_url = source_url

        self.user_name = user_name
        self.user_email = user_email

        catalog_path = HipsDefaultValues.app_cache_dir.value.joinpath(self.catalog_name)

        self.catalog = Catalog(catalog_id=self.catalog_name, path=catalog_path, src=self.server_url)
        self.repo = None

        self._configure_git()

    def _configure_git(self):
        self.repo.config_writer().set_value("user", "name", self.user_name).release()
        self.repo.config_writer().set_value("user", "email", self.user_email).release()

        # switch to ssh url if not already set
        if not self.repo.remote().url.startswith("git"):
            self.repo.remote().set_url(get_ssh_url(self.project_path, self.server_url))

    def pre_release(self, dry_run=False):
        """Performs all operation to release the branch in the given repo, but does not publish yet.

        Args:
            dry_run:
                Boolean flag, if True, no commit will happen, but an info is shown.

        Returns:
            True.

        """
        if self.target_url != self.source_url:
            raise RuntimeError("CI Routine only works for a merge request within the same project!")

        self.repo = self.catalog.download()

        module_logger().info("Branch name: %s" % self.branch_name)

        # checkout branch
        head = checkout_branch(self.repo.working_tree_dir, self.branch_name)

        # get the yml file to release
        yml_file_path = retrieve_yml_file_path(head)
        yml_dict = get_dict_from_yml(yml_file_path)

        # get metadata from yml_file
        try:
            deposit_id = yml_dict["deposit_id"]
        except KeyError:
            deposit_id = None
        solution_name = yml_dict["name"]

        # get the solution file to release
        solution_file = retrieve_solution_file_path(head)

        # get the release deposit. Either a new one or an existing one to perform an update
        deposit = zenodo_get_deposit(solution_name, solution_file, deposit_id)

        # alter the files in the merge request to include the DOI
        # Todo: really necessary? It is hacky...
        solution_file = set_zenodo_metadata_in_solutionfile(
            solution_file,
            deposit.metadata.prereserve_doi["doi"],
            deposit.id
        )

        # include doi and ID in yml
        yml_dict["doi"] = deposit.metadata.prereserve_doi["doi"]
        yml_dict["deposit_id"] = deposit.id
        write_dict_to_yml(yml_file_path, yml_dict)

        # zenodo upload solution but not publish
        zenodo_upload(deposit, solution_file)

        # update catalog index
        self.catalog.catalog_index.update(yml_dict)
        self.catalog.catalog_index.save()

        # push changes to catalog, do not trigger pipeline
        commit_msg = "CI updated %s" % solution_name
        add_files_commit_and_push(
            head,
            [yml_file_path, solution_file, self.catalog.index_path],
            commit_msg,
            dry_run=dry_run,
            trigger_pipeline=False
        )

        return True

    def release(self):
        """Releases the solution files in the branch of a catalog repository.

        Returns:
            The published deposit.

        """
        self.repo = self.catalog.download()

        # checkout branch
        head = checkout_branch(self.repo.working_tree_dir, self.branch_name)

        # get the solution file to release
        solution_file = retrieve_solution_file_path(head)

        # get the yml file to release
        yml_file_path = retrieve_yml_file_path(head)
        yml_dict = get_dict_from_yml(yml_file_path)

        deposit_id = get_yml_entry(yml_dict, "deposit_id", allow_none=True)
        solution_name = get_yml_entry(yml_dict, "name", allow_none=False)

        # retrieve the deposit from the id
        deposit = zenodo_get_deposit(solution_name, solution_file, deposit_id)

        # publish to zenodo
        deposit.publish()

        return True

    def solution_test(self, path):
        """Reads in a solution and executes the testing routine.

        Returns:
            True when the test routine succeeds, False otherwise.

        """
        pass

        # install solution

        # create script for running testing

        # execute in target env.

        # retrieve return value and evaluate
