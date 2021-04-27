import os
from urllib.parse import urlparse

import yaml

from hips.ci import zenodo_api
from hips.core.model import logging
from hips.core.utils.operations.git_operations import _retrieve_single_file_from_head

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

module_logger = logging.get_active_logger


def _get_ci_deploy_values():
    """Reads out the environment variables for CI routines"""
    branch_name = get_os_environment_value(ci_source_branch_name)
    catalog_name = get_os_environment_value(ci_target_catalog_name)
    target_url = get_os_environment_value(ci_mr_target_url)
    source_url = get_os_environment_value(ci_mr_source_url)

    module_logger().debug("Read out the folowing variabels and their values:\n"
                          "\t - branch name:  %s\n"
                          "\t - catalog name: %s\n"
                          "\t - target url: %s\n"
                          "\t - source url: %s" % (branch_name, catalog_name, target_url, source_url))

    return [branch_name, catalog_name, target_url, source_url]


def _get_ci_git_config_values():
    user_name = get_os_environment_value(ci_user_name)
    user_email = get_os_environment_value(ci_user_email)

    module_logger().debug("User: %s ; Email: %s" % (user_name, user_email))

    return [user_name, user_email]


def _get_ssh_url():
    project_path = get_os_environment_value(ci_project_path)
    server_url = get_os_environment_value(ci_server_url)
    parsed_url = urlparse(server_url)

    ssh_url = 'git@%s:%s' % (parsed_url.netloc, project_path)

    module_logger().debug("Set remote URL to %s" % ssh_url)

    return ssh_url


def _zenodo_upload(deposit, solution_file):
    """ Uploads a solution file to a ZenodoDeposit. Expects the deposit to be writable. (e.g. unpublished)

    Args:
        deposit:
            The deposit to upload to.
        solution_file:
            The solution file to upload.

    Returns:
        The updated deposit.

    """
    _, solution_name_full = _parse_solution_name_from_file_path(solution_file)

    if solution_name_full in deposit.files:  # File does exist
        module_logger().debug("Update solution file %s to Zenodo deposit with id %s" % (solution_name_full, deposit.id))
        deposit.update_file(solution_name_full, solution_file)
    else:
        module_logger().debug("Create solution file %s in Zenodo deposit with id %s" % (solution_name_full, deposit.id))
        deposit.create_file(solution_file)

    return deposit


def _zenodo_get_deposit(solution_name, solution_file, deposit_id):
    """Querys zenodo to get the deposit of the solution_file. Creates an empty deposit if no deposit exists.

    Args:
        solution_file:
            The solution file to receive the deposit of.
        deposit_id:
            The deposit ID of the deposit the solution file lives in.

    Returns:
        The deposit. Either brand-new, or the one holding the solution file.

    Raises:
        AttributeError:
           When the deposit is already published but does NOT hold the file it should hold.
           When the unpublished deposit holds a solution file, but it is not the one expected.

        RuntimeError:
            When the deposit ID is given but no deposit can be found.
            When the unpublished deposit has no prereserved doi.

    """
    _, solution_file_name_full = _parse_solution_name_from_file_path(solution_file)

    query = __get_zenodo_api()

    if deposit_id:  # case deposit already exists
        module_logger().debug("ID given. Searching for already published deposit with ID %s..." % deposit_id)
        deposit = query.deposit_get(deposit_id)

        if deposit and deposit[0].submitted:  # case published
            deposit = deposit[0]

            if solution_file_name_full not in deposit.files:
                raise AttributeError('Deposit has no file with the name %s!' % solution_file_name_full)

            module_logger().debug("Deposit with id %s found. Querying new version..." % deposit.id)

            deposit = deposit.new_version()  # only query new version IFF file exists
        else:  # case unpublished
            module_logger().debug("ID not published. Searching for drafts...")
            deposit = query.deposit_get(deposit_id, status=zenodo_api.DepositStatus.DRAFT)

            if not deposit:
                raise RuntimeError("Could not find deposit with id %s" % deposit_id)

            deposit = deposit[0]

            module_logger().debug("Deposit with id %s found..." % deposit.id)

            if len(deposit.files) != 0:
                if len(deposit.files) > 1 or solution_file_name_full not in deposit.files:
                    raise AttributeError('Deposit has no file with the name %s!' % solution_file_name_full)

            if deposit.metadata is None \
                    or not isinstance(deposit.metadata.prereserve_doi, dict) \
                    or "doi" not in deposit.metadata.prereserve_doi.keys():
                raise RuntimeError("Deposit has no prereserved DOI!")

    else:  # case deposit does not exist
        module_logger().debug("Query new deposit with DOI...")
        deposit = query.deposit_create_with_prereserve_doi(solution_name)

    return deposit


def _retrieve_solution_file(head):
    """Get back the solution file in the top commit of the given head."""
    return _retrieve_single_file_from_head(head, "solutions/")


def _retrieve_yml_file(head):
    """Get back the yml file in the top commit of the given head."""
    return _retrieve_single_file_from_head(head, "catalog/")


def get_os_environment_value(env_name):
    """ Reads out the given environment value from the environment variable given."""
    try:
        module_logger().debug("Fetching environment variable named %s" % env_name)
        return os.environ[env_name]
    except KeyError:
        raise KeyError("Environment variable %s not set!" % env_name)


# ToDo: better environment parsing?
def __get_zenodo_api():
    """Returns the zenodo connection. Caution: Using values in the environment variables which must be set."""
    return zenodo_api.ZenodoAPI(
        get_os_environment_value(ci_zenodo_base_url),
        get_os_environment_value(ci_zenodo_access_token)
    )


def _parse_solution_name_from_file_path(solution_file):
    """Extracts the name of the solution from the absolute path of the solution file."""
    solution_name, solution_ext = os.path.splitext(os.path.basename(solution_file))
    solution_name_full = solution_name + solution_ext

    module_logger().debug("Solution file named: %s " % solution_name_full)

    return solution_name, solution_name_full


# ToDo: write tests
def _get_entry_from_yml(yml_file, entry_name):
    """Reads out metadata of a yml file"""
    with open(yml_file, 'r') as yml_f:
        d = yaml.safe_load(yml_f)

    try:
        return d[entry_name]
    except KeyError:
        return None


# ToDo: write tests
def _add_dict_entry_to_yml(yml_file, metadata, value):
    """Writes metadata in a yml file"""
    with open(yml_file, 'r') as yml_f:
        d = yaml.safe_load(yml_f)

    d[metadata] = value

    with open(yml_file, 'w') as yml_f:
        yml_f.write(yaml.dump(d, Dumper=yaml.Dumper))


# ToDo: write tests
def _yaml_to_md(yml_file, md_file):
    with open(yml_file, 'r') as yml_f:
        d = yaml.safe_load(yml_f)

    with open(md_file, 'w+') as md_f:
        md_f.write("---\n" + yaml.dump(d, Dumper=yaml.Dumper) + "\n---")




