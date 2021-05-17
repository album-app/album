from hips import core
import hips.core.utils.operations.git_operations
from hips.ci.ci_utils import _get_ci_deploy_values, _retrieve_solution_file, \
    _zenodo_get_deposit
from hips.core.model import logging
from hips.core.utils.operations.file_operations import get_zenodo_metadata
from hips.core.utils.operations.git_operations import checkout_branch

module_logger = logging.get_active_logger


def ci_release():
    branch_name, catalog_name, target_url, source_url = _get_ci_deploy_values()

    if target_url != source_url:
        raise RuntimeError("CI Routine only works for a merge request within the same project!")

    module_logger().info("Download catalog \"%s\" from %s..." % (catalog_name, source_url))
    repo = hips.core.utils.operations.git_operations.download_repository(source_url, catalog_name)

    module_logger().info("Branch name: %s" % branch_name)

    release(str(repo.working_tree_dir), branch_name)


def release(git_repo_path, branch_name):
    """Releases the solution files in the branch of a catalog repository.

    Args:
        git_repo_path:
            The catalog repository path.
        branch_name:
            The branch name.

    Returns:
        The published deposit.

    """
    # checkout branch
    head = checkout_branch(git_repo_path, branch_name)

    # get the solution file to deploy
    solution_file = _retrieve_solution_file(head)
    # todo: get this from yaml or index!
    deposit_id = get_zenodo_metadata(solution_file, "deposit_id")

    # retrieve the deposit from the id
    deposit = _zenodo_get_deposit(solution_file, deposit_id)

    # publish to zenodo
    deposit.publish()

    return True
