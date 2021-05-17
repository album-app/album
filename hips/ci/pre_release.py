import os
from pathlib import Path

from xdg import xdg_cache_home

import hips.core.utils.operations.git_operations
from hips.ci.ci_utils import _get_ci_deploy_values, _retrieve_solution_file, \
    _zenodo_upload, _retrieve_yml_file, _zenodo_get_deposit, _get_entry_from_yml, _add_dict_entry_to_yml, \
    _get_ssh_url, _get_ci_git_config_values
from hips.core.model import logging
from hips.core.model.catalog import CatalogIndex
from hips.core.model.configuration import HipsDefaultValues
from hips.core.utils.operations.file_operations import get_dict_from_yml
from hips.core.utils.operations.git_operations import checkout_branch, add_files_commit_and_push

module_logger = logging.get_active_logger


def ci_pre_release():
    """Routine to upload the hips deploy to zenodo

    Expects the CI runner to be configured in a way that:

    - ssh is configured such that a connection to version control/management can be established.
        (e.g. `ssh -T git@gitlab.com`  works.)
    - The CI runner has the following environment variables defined:
        "ZENODO_ACCESS_TOKEN"                   - the access token to access the zenodo API
        "ZENODO_BASE_URL"                       - the zenodo URL (e.g. sandbox, non-sandbox)
        "CI_PROJECT_NAME"                       - the project name
        "CI_MERGE_REQUEST_PROJECT_URL"          - the url of the merge request project
        "CI_MERGE_REQUEST_SOURCE_PROJECT_URL"   - the url of the source project
        "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"   - the branch name of the source project
        "CI_PROJECT_PATH"                       - the path to the project
                (e.g. for https://gitlab.com/gitlab-org/gitlab would expect it to be "/gitlab-org/gitlab"
        "CI_SERVER_URL"                         - the url to the server (for gitlab: https://gitlab.com)
        "CI_USER_NAME"                          - the desired username of
                the user performing push operations to the repository
        "CI_USER_EMAIL"                         - the desired email of
                the user performing push operations to the repository

    """
    branch_name, catalog_name, target_url, source_url = _get_ci_deploy_values()

    if target_url != source_url:
        raise RuntimeError("CI Routine only works for a merge request within the same project!")

    module_logger().info("Download catalog \"%s\" from %s..." % (catalog_name, source_url))

    catalog_path = xdg_cache_home().joinpath(catalog_name)

    repo = hips.core.utils.operations.git_operations.download_repository(source_url, catalog_path)

    # configure git
    user_name, user_email = _get_ci_git_config_values()
    repo.config_writer().set_value("user", "name", user_name).release()
    repo.config_writer().set_value("user", "email", user_email).release()

    # switch to ssh url if not already set
    if not repo.remote().url.startswith("git"):
        repo.remote().set_url(_get_ssh_url())

    module_logger().info("Branch name: %s" % branch_name)

    pre_release(str(repo.working_tree_dir), branch_name)  # a call from the CI to do the pre-release


def pre_release(git_repo_path, branch_name):
    """Performs all operation to release the branch in the given repo, but does not publish yet.

    Args:
        git_repo_path:
            The absolute path to the catalog repository.
        branch_name:
            The branch name holding the commit with the solution file to release.

    Returns:
        The zenodo deposit.

    """
    # checkout branch
    head = checkout_branch(git_repo_path, branch_name)

    # get the yml file to release
    yml_file = _retrieve_yml_file(head)

    # get metadata from yml_file
    deposit_id = _get_entry_from_yml(yml_file, "deposit_id")
    solution_name = _get_entry_from_yml(yml_file, "name")

    # get the solution file to release
    solution_file = _retrieve_solution_file(head)

    # get the release deposit. Either a new one or an existing one to perform an update
    deposit = _zenodo_get_deposit(solution_name, solution_file, deposit_id)

    # alter the files in the merge request to include the DOI
    # Todo: really necessary? It is hacky...
    solution_file = hips.core.utils.operations.file_operations.set_zenodo_metadata_in_solutionfile(
        solution_file,
        deposit.metadata.prereserve_doi["doi"],
        deposit.id
    )

    # include doi and ID in yml
    _add_dict_entry_to_yml(yml_file, "doi", deposit.metadata.prereserve_doi["doi"])
    _add_dict_entry_to_yml(yml_file, "deposit_id", deposit.id)

    # zenodo upload solution but not publish
    _zenodo_upload(deposit, solution_file)

    # update catalog index
    catalog_file = Path(git_repo_path).joinpath(HipsDefaultValues.catalog_index_file_name.value)
    catalog_index = CatalogIndex(name="", path=catalog_file)
    catalog_index.update(get_dict_from_yml(yml_file))
    catalog_index.save()

    # push changes to catalog, do not trigger pipeline
    commit_msg = "CI updated %s" % solution_name
    add_files_commit_and_push(
        head, [yml_file, solution_file, catalog_file], commit_msg, dry_run=False, trigger_pipeline=False
    )

    return True

