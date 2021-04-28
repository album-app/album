import os

import yaml

from hips.core import get_active_hips, load_and_push_hips
from hips.core.model import logging
from hips.core.utils.operations.git_operations import _add_files_commit_and_push, _copy_solution_to_repository, \
    __create_new_head

module_logger = logging.get_active_logger

deploy_keys = [
    'group', 'name', 'description', 'version', 'format_version', 'tested_hips_version',
    'min_hips_version', 'license', 'git_repo', 'authors', 'cite', 'tags', 'documentation',
    'covers', 'sample_inputs', 'sample_outputs', 'args', 'title'
]


def get_hips_deploy_dict(active_hips):
    """Return a dictionary with the relevant deployment key/values for a given hips."""
    d = {}

    for k in deploy_keys:
        d[k] = active_hips[k]

    return _remove_action_from_args(d)


def _remove_action_from_args(hips_dict):
    for arg in hips_dict["args"]:
        if isinstance(arg, dict):
            if "action" in arg.keys():
                arg.pop("action")

    return hips_dict


def _create_yaml_file_in_repo(repo, active_hips):
    """Creates a Markdown file in the given repo for the given solution.

    Args:
        repo:
            The repo of the catalog.
        active_hips:
            The active hips object.

    Returns:
        The Path to the created markdown file.

    """
    yaml_str = _create_yml_string(active_hips)
    yaml_path = os.path.join(repo.working_tree_dir, "catalog", "%s%s" % (active_hips['name'], ".yml"))

    module_logger().info('writing to: %s...' % yaml_path)
    with open(yaml_path, 'w') as f:
        f.write(yaml_str)

    return yaml_path


# Todo: write tests
def _create_yml_string(active_hips):
    """Creates the yaml string with all relevant information"""
    d = get_hips_deploy_dict(active_hips)
    module_logger().debug('Create yaml file from solution...')
    return yaml.dump(d, Dumper=yaml.Dumper)


# Todo: write tests
def _create_hips_merge_request(repo, file_paths, active_hips, dry_run=False):
    """Creates a merge request to the catalog repository for the hips object.

    Commits first the files given in the call, but will not include anything else than that.

    Args:
        repo:
            The catalog repository.
        file_paths:
            A list of files to include in the merge request. Can be relative to the catalog repository path or absolute.
        active_hips:
            The active hips object.
        dry_run:
            Option to only show what would happen. No Merge request will be created.

    Raises:
        RuntimeError when no differences to the previous commit can be found.

    """
    # make a new branch and checkout
    new_head = __create_new_head(repo, active_hips['name'])
    new_head.checkout()

    commit_mssg = "Adding new/updated %s" % active_hips["name"]

    _add_files_commit_and_push(new_head, file_paths, commit_mssg, dry_run)


# Todo: write tests
def deploy(args):
    """Function corresponding to the `deploy` subcommand of `hips`.

    Generates the yml for a hips and creates a merge request to the catalog only
    including the markdown and solution file.

    """
    # if imported at the beginning creates a circular dependency!
    from hips.core import HipsConfiguration

    hips_config = HipsConfiguration()

    load_and_push_hips(args.path)
    active_hips = get_active_hips()

    # run installation of new solution file in debug mode
    # Todo: call the installation routine

    default_deploy_catalog = hips_config.get_default_deployment_catalog()
    repo = default_deploy_catalog.download()

    # copy script to repository
    solution_file = _copy_solution_to_repository(args.path, repo, active_hips)

    # create solution yml file
    yml_file = _create_yaml_file_in_repo(repo, active_hips)

    # create merge request
    _create_hips_merge_request(repo, [yml_file, solution_file], active_hips)
