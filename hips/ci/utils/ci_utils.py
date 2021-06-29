import os
from urllib.parse import urlparse

from hips.ci import zenodo_api
from hips.ci.utils.deploy_environment import get_ci_zenodo_values
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.git_operations import retrieve_single_file_from_head
from hips_runner import logging

module_logger = logging.get_active_logger


def get_ssh_url(project_path, server_http_url):
    parsed_url = urlparse(server_http_url)

    ssh_url = 'git@%s:%s' % (parsed_url.netloc, project_path)

    module_logger().debug("Set remote URL to %s..." % ssh_url)

    return ssh_url


def zenodo_upload(deposit, solution_file):
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
        module_logger().debug(
            "Update solution file %s to Zenodo deposit with id %s..." % (solution_name_full, deposit.id)
        )
        deposit.update_file(solution_name_full, solution_file)
    else:
        module_logger().debug(
            "Create solution file %s in Zenodo deposit with id %s..." % (solution_name_full, deposit.id)
        )
        deposit.create_file(solution_file)

    return deposit


def zenodo_get_deposit(solution_name, solution_file, deposit_id):
    """Querys zenodo to get the deposit of the solution_file. Creates an empty deposit if no deposit exists.

    Args:
        solution_file:
            The solution file to receive the deposit from.
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

    query = get_zenodo_api()

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


def retrieve_solution_file_path(head):
    """Get back the solution file in the top commit of the given head."""
    return retrieve_single_file_from_head(head, HipsDefaultValues.cache_path_solution_prefix.value)


def retrieve_yml_file_path(head):
    """Get back the yml file in the top commit of the given head."""
    return retrieve_single_file_from_head(head, HipsDefaultValues.catalog_yaml_prefix.value)


def get_zenodo_api():
    """Returns the zenodo connection. Caution: Using values in the environment variables which must be set."""

    zenodo_base_url, zenodo_access_token = get_ci_zenodo_values()

    return zenodo_api.ZenodoAPI(
        zenodo_base_url,
        zenodo_access_token
    )


def _parse_solution_name_from_file_path(solution_file):
    """Extracts the name of the solution from the absolute path of the solution file."""
    solution_name, solution_ext = os.path.splitext(os.path.basename(solution_file))
    solution_name_full = solution_name + solution_ext

    module_logger().debug("Solution file named: %s..." % solution_name_full)

    return solution_name, solution_name_full
