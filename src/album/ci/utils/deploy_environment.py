import os

from album.runner import album_logging

"""Environment variables for the CI:

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

# user defined variables:
ci_user_name = "CI_USER_NAME"
ci_user_email = "CI_USER_EMAIL"
ci_zenodo_access_token = 'ZENODO_ACCESS_TOKEN'
ci_zenodo_base_url = 'ZENODO_BASE_URL'

# basic CI variables
ci_target_catalog_name = "CI_PROJECT_NAME"
ci_mr_target_url = "CI_MERGE_REQUEST_PROJECT_URL"
ci_mr_source_url = "CI_MERGE_REQUEST_SOURCE_PROJECT_URL"
ci_source_branch_name = "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME"
ci_project_path = "CI_PROJECT_PATH"
ci_server_url = "CI_SERVER_URL"

module_logger = album_logging.get_active_logger


def get_os_environment_value(env_name):
    """ Reads out the given environment value from the environment variable given."""
    try:
        module_logger().debug("Fetching environment variable named %s..." % env_name)
        return os.environ[env_name]
    except KeyError:
        raise KeyError("Environment variable %s not set!" % env_name)


def get_ci_deploy_values():
    """Reads out the environment variables for CI routines"""
    branch_name = get_os_environment_value(ci_source_branch_name)
    catalog_name = get_os_environment_value(ci_target_catalog_name)
    target_url = get_os_environment_value(ci_mr_target_url)
    source_url = get_os_environment_value(ci_mr_source_url)

    module_logger().debug("Read out the following variables and their values:\n"
                          "\t - branch name:  %s\n"
                          "\t - catalog name: %s\n"
                          "\t - target url: %s\n"
                          "\t - source url: %s" % (branch_name, catalog_name, target_url, source_url))

    return [branch_name, catalog_name, target_url, source_url]


def get_ci_git_config_values():
    user_name = get_os_environment_value(ci_user_name)
    user_email = get_os_environment_value(ci_user_email)

    module_logger().debug("User: %s ; Email: %s" % (user_name, user_email))

    return [user_name, user_email]


def get_ci_project_values():
    project_path = get_os_environment_value(ci_project_path)
    server_url = get_os_environment_value(ci_server_url)

    module_logger().debug("project_path: %s ; server_url: %s" % (project_path, server_url))

    return [project_path, server_url]


def get_ci_zenodo_values():
    zenodo_base_url = get_os_environment_value(ci_zenodo_base_url),
    zenodo_access_token = get_os_environment_value(ci_zenodo_access_token)

    module_logger().debug("zenodo_base_url: %s ; zeneodo_access_token: successfully read out!" % zenodo_base_url)

    return [zenodo_base_url, zenodo_access_token]
