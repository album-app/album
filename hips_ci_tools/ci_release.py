from hips.deploy import pre_release, get_os_environment_value
from install_helper import modules
from utils import hips_logging

ci_target_catalog_name = "CI_PROJECT_NAME"
ci_mr_target_url = "CI_MERGE_REQUEST_PROJECT_URL"
ci_mr_source_url = "CI_MERGE_REQUEST_SOURCE_PROJECT_URL"
ci_source_branch_name = "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"
ci_pwd = "PWD"

module_logger = hips_logging.get_active_logger


def ci_pre_release():
    branch_name = get_os_environment_value(ci_source_branch_name)
    catalog_name = get_os_environment_value(ci_target_catalog_name)
    target_url = get_os_environment_value(ci_mr_target_url)
    source_url = get_os_environment_value(ci_mr_source_url)

    if target_url != source_url:
        raise RuntimeError("CI Routine only works for a merge request within the same project!")

    module_logger().info("Download catalog \"%s\" from %s..." % (catalog_name, source_url))
    repo = modules.download_repository(source_url, catalog_name)

    module_logger().info("Branch name: %s" % branch_name)

    pre_release(str(repo.working_tree_dir), branch_name)  # a call from the CI to do the pre-release


def ci_release():
    pass
