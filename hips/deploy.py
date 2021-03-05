import yaml
import hips
from hips import get_active_hips
import logging
from hips import Hips, get_active_hips
from install_helper import modules
import os
import git
import shutil


module_logger = logging.getLogger('hips')


def hips_deploy_dict(active_hips):
    """Return a dictionary with the relevant deployment key/values for a given hips."""
    d = {}

    deploy_keys = [
        'group', 'name', 'description', 'timestamp', 'version', 'format_version', 'tested_hips_version',
        'min_hips_version', 'license', 'git_repo', 'authors', 'cite', 'tags', 'documentation',
        'covers', 'sample_inputs', 'sample_outputs', 'args', 'doi'
    ]

    for k in deploy_keys:
        d[k] = active_hips[k]

    return d


def extract_catalog_name(catalog_repo):
    """Extracts a basename from a repository URL.

    Args:
        catalog_repo:
            The repository URL or ssh string of the catalog.

    Returns:
        The basename of the repository

    """
    name, _ = os.path.splitext(os.path.basename(catalog_repo))
    return name


def deploy(args):
    """Function corresponding to the `deploy` subcommand of `hips`.

    Generates the yml for a hips and creates a merge request to the catalog.

    Raises:
        GitCommandError: When there is an error with gitpython.
    """
    module_logger.debug('Load hips...')
    hips_script = open(args.path).read()
    exec(hips_script)
    active_hips = get_active_hips()
    d = hips_deploy_dict(active_hips)

    # download (or update) catalog
    catalog_url = active_hips['catalog']
    catalog_name = extract_catalog_name(catalog_url)
    module_logger.debug("Donwload catalog %s to the name %s" % (catalog_url, catalog_name))
    repo = modules.download_repository(catalog_url, catalog_name)

    # make a new branch and checkout
    new_head = repo.create_head(active_hips['name'])
    new_head.checkout()

    # create new solution markdown file
    module_logger.debug('Create yaml file from solution...')
    yaml_str = yaml.dump(d, Dumper=yaml.Dumper)
    yaml_path = os.path.join(repo.working_tree_dir, "_solutions", "%s%s" % (active_hips['name'], ".md"))

    module_logger.info('writing to: %s' % yaml_path)

    with open(yaml_path, 'w') as f:
        f.write("---\n" + yaml_str + "\n---")

    # copy script to repository
    solution_file = os.path.join(repo.working_tree_dir, "solutions", "%s%s" % (active_hips['name'], ".py"))
    shutil.copy(args.path, solution_file)

    # create merge request
    if repo.index.diff() or repo.untracked_files:
        module_logger.info('Creating a merge request...')
        repo.git.add(solution_file)
        repo.git.add(yaml_path)
        repo.git.commit(m="Adding new/updated %s" % active_hips['name'])
        try:
            module_logger.debug("Running command: repo.git.push('--set-upstream',"
                                " '--push-option=merge_request.create', 'origin', %s)..." % new_head)
            repo.git.push('--set-upstream', '--push-option=merge_request.create', 'origin', new_head)
            # see https://docs.gitlab.com/ee/user/project/push_options.html
        except git.GitCommandError as err:
            module_logger.error(err.stderr)
            raise
    else:
        message = "Diff shows no changes to the repository. Is the solution already deployed? Aborting..."
        module_logger.error(message)
        raise RuntimeError(message)


def zenodo_upload():
    # check for new solution files
    # upload new solution files
    # alter DOI of solution
    # merge
    pass

