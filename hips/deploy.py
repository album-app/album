import os
import shutil

import git
import yaml

from hips import get_active_hips, load_and_push_hips
from install_helper import modules
from utils import file_operations, zenodo_api, hips_logging

module_logger = hips_logging.get_active_logger

ci_zenodo_access_token_environment_name = 'ZENODO_ACCESS_TOKEN'
ci_zenodo_base_url_environment_name = 'ZENODO_BASE_URL'

deploy_keys = [
    'group', 'name', 'description', 'version', 'format_version', 'tested_hips_version',
    'min_hips_version', 'license', 'git_repo', 'authors', 'cite', 'tags', 'documentation',
    'covers', 'sample_inputs', 'sample_outputs', 'args',
]


def _hips_deploy_dict(active_hips):
    """Return a dictionary with the relevant deployment key/values for a given hips."""
    d = {}

    for k in deploy_keys:
        d[k] = active_hips[k]

    return d


def _extract_catalog_name(catalog_repo):
    """Extracts a basename from a repository URL.

    Args:
        catalog_repo:
            The repository URL or ssh string of the catalog.

    Returns:
        The basename of the repository

    """
    name, _ = os.path.splitext(os.path.basename(catalog_repo))
    return name


def download_catalog(active_hips):
    """Downloads the catalog specified in hips object.

    Args:
        active_hips:
            The hips object.

    Returns:
        The catalog repository as Repo object

    """
    catalog_url = active_hips['catalog']
    catalog_name = _extract_catalog_name(catalog_url)  # only the folder name of the local catalog git repo
    module_logger().debug("Donwload catalog %s to the name %s" % (catalog_url, catalog_name))
    repo = modules.download_repository(catalog_url, catalog_name)

    return repo


def _create_markdown_file(repo, active_hips):
    """Creates a Markdown file in the given repo for the given solution

    Args:
        repo:
            The repo of the catalog.
        active_hips:
            The active hips object.

    Returns:
        The Path to the created markdown file.

    """
    d = _hips_deploy_dict(active_hips)
    module_logger().debug('Create yaml file from solution...')
    yaml_str = yaml.dump(d, Dumper=yaml.Dumper)
    yaml_path = os.path.join(repo.working_tree_dir, "_solutions", "%s%s" % (active_hips['name'], ".md"))

    module_logger().info('writing to: %s' % yaml_path)
    with open(yaml_path, 'w') as f:
        f.write("---\n" + yaml_str + "\n---")

    return yaml_path


def __create_new_head(repo, name):
    """Force creates a new head of a given name in a repository and returns the head."""

    if name in repo.heads:
        git.Head.delete(repo, name, force=True)
    new_head = repo.create_head(name)

    return new_head


def _create_merge_request(repo, file_paths, active_hips, dry_run=False):
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

    if repo.index.diff() or repo.untracked_files:
        module_logger().info('Creating a merge request...')

        for file_path in file_paths:
            module_logger().debug('Adding file %s...' % file_path)
            repo.git.add(file_path)

        repo.git.commit(m="Adding new/updated %s" % active_hips['name'])

        try:
            module_logger().debug("Running command: repo.git.push('--set-upstream',"
                                  " '--push-option=merge_request.create', '-f', 'origin', %s)..." % new_head)
            if not dry_run:
                    repo.git.push('--set-upstream', '--push-option=merge_request.create', '-f', 'origin', new_head)
                    # see https://docs.gitlab.com/ee/user/project/push_options.html
        except git.GitCommandError as err:
            module_logger().error(err.stderr)
            raise
    else:
        raise RuntimeError("Diff shows no changes to the repository. Is the solution already deployed? Aborting...")


def _copy_solution_to_repository(path, repo, active_hips):
    """Copys a solution outside the catalog repository to the correct path inside the catalog repository.

    Args:
        path:
            The solution file.
        repo:
            The catalog repository.
        active_hips:
            The active hips object.

    Returns:
        The path to the solution file in the correct folder inside the catalog repository.

    """
    abs_path_solution_file = os.path.join(repo.working_tree_dir, "solutions", "%s%s" % (active_hips['name'], ".py"))
    module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_file))
    shutil.copy(path, abs_path_solution_file)

    return abs_path_solution_file


# toDo: str as Path?
def _retrieve_solution_file(head):
    """Extracts the solution file from the given branch (or head) of the catalog repository.

     Solution file should NOT BE ALREADY COMMITTED!

    Args:
        head:
            The branch (or more general head) of the catalog repository where the solution file was committed in.

    Returns:
        The absolute path of the solution file (in the catalog repository).

    Raises:
        RuntimeError when
            a) there is no parent commit in the head
            b) No solution file is included in the latest commit of the given head
            c) There are more than a single solution file committed in the latest commit.

    """
    parent = head.commit.parents[0] if head.commit.parents else None
    module_logger().debug("Found head commit: %s" % parent)
    module_logger().debug("Summary message: %s" % parent.summary)

    if not parent:
        raise RuntimeError("Cannot execute diff since there is only a single commit!")

    diff = head.commit.diff(parent)

    abs_path_solution_file = []
    for file in diff:
        module_logger().debug("Found file in commit diff to parent: %s " % file.a_path)
        if file.a_path.startswith('solutions/'):
            abs_path_solution_file.append(os.path.join(head.repo.working_tree_dir, file.a_path))

    if not abs_path_solution_file:
        raise RuntimeError("Illegal merge request! Found no solution to release! Aborting...")
    if len(abs_path_solution_file) > 1:
        raise RuntimeError("Illegal merge request! Found too many solutions to release! Aborting...")

    return abs_path_solution_file[0]


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
        get_os_environment_value(ci_zenodo_base_url_environment_name),
        get_os_environment_value(ci_zenodo_access_token_environment_name)
    )


def _parse_solution_name_from_file_path(solution_file):
    """Extracts the name of the solution from the absolute path of the solution file."""
    solution_name, solution_ext = os.path.splitext(os.path.basename(solution_file))
    solution_name_full = solution_name + solution_ext

    module_logger().debug("Solution file named: %s " % solution_name_full)

    return solution_name, solution_name_full


def _zenodo_get_deposit(solution_file, deposit_id):
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
    solution_name, solution_name_full = _parse_solution_name_from_file_path(solution_file)

    query = __get_zenodo_api()

    if deposit_id:  # case deposit already exists
        module_logger().debug("ID given. Searching for already published deposit with ID %s..." % deposit_id)
        deposit = query.deposit_get(deposit_id)

        if deposit:  # case published
            deposit = deposit[0]

            if solution_name_full not in deposit.files:
                raise AttributeError('Deposit has no file with the name %s!' % solution_name_full)

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
                if len(deposit.files) > 1 or solution_name_full not in deposit.files:
                    raise AttributeError('Deposit has no file with the name %s!' % solution_name_full)

            if deposit.metadata is None \
                    or not isinstance(deposit.metadata.prereserve_doi, dict) \
                    or "doi" not in deposit.metadata.prereserve_doi.keys():
                raise RuntimeError("Deposit has no prereserved DOI!")

    else:  # case deposit does not exist
        module_logger().debug("Query new deposit with DOI...")
        deposit = query.deposit_create_with_prereserve_doi(solution_name)

    return deposit


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


def _checkout_branch(git_repo_path, branch_name):
    repo = git.Repo(git_repo_path)
    module_logger().debug("Repository found in %s..." % git_repo_path)

    try:  # checkout branch locally
        module_logger().debug("Found the following branches locally: \n %s " % "\n".join([h.name for h in repo.heads]))
        head = repo.heads[branch_name]
        return head
    except IndexError as e:
        module_logger().debug("Branch name not in local repository! Checking origin...")
        for remote in repo.remotes:  # checkout branch remote
            try:
                module_logger().debug("Trying remote: %s..." % remote.name)
                head = remote.refs[branch_name].checkout()
                return head
            except IndexError:
                module_logger().debug("Not found! Trying next...")
        module_logger().debug("Nothing left to try...")
        raise IndexError("Branch %s not in repository!" % branch_name) from e


def get_release_deposit(solution_file):
    """Receives the release deposit to publish to.

    Args:
        solution_file:
            The solution file to get deposit from.

    Returns:
        The deposit that was written to and the solution file.

    """

    # get zenodo id information from solution file
    deposit_id = file_operations.get_zenodo_metadata(solution_file, "deposit_id")

    # query deposit
    deposit = _zenodo_get_deposit(solution_file, deposit_id)

    return deposit, solution_file


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
    head = _checkout_branch(git_repo_path, branch_name)

    # get the solution file to deploy
    solution_file = _retrieve_solution_file(head)

    # get the release deposit. Either a new one or an existing one to perform an update
    deposit, solution_file = get_release_deposit(solution_file)

    # alter the files in the merge request to have the DOI
    solution_file = file_operations.set_zenodo_metadata_in_solutionfile(
        solution_file, deposit.metadata.prereserve_doi["doi"],
        deposit.id
    )

    # zenodo upload solution but not publish
    _zenodo_upload(deposit, solution_file)

    return deposit


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
    # ToDo: integrate this in the CI
    deposit = pre_release(git_repo_path, branch_name)

    # commit changes and push but DO NOT TRIGGER PIPELINE!

    return deposit.publish()


def deploy(args):
    """Function corresponding to the `deploy` subcommand of `hips`.

    Generates the yml for a hips and creates a merge request to the catalog only
    including the markdown and solution file.

    """
    load_and_push_hips(args.path)
    active_hips = get_active_hips()

    # run installation of new solution file in debug modus
    # Todo: call the installation routine

    repo = download_catalog(active_hips)

    # create solution markdown file
    markdown_file = _create_markdown_file(repo, active_hips)

    # copy script to repository
    solution_file = _copy_solution_to_repository(args.path, repo, active_hips)

    # create merge request
    _create_merge_request(repo, [markdown_file, solution_file], active_hips)
