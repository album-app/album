import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from urllib.parse import urlparse

import git
from git import Repo

from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.url_operations import is_url
from album.runner import album_logging

module_logger = album_logging.get_active_logger


def checkout_branch(git_repo, branch_name):
    """Checks out a branch on a repository.

    First, local refs are taken, then refs pointing to origin.

    Args:
        git_repo:
            The repository
        branch_name:
            The name of the branch to check out

    Returns:
        The head of the branch

    Raises:
        IndexError when the branch is no where available.

    """
    try:  # checkout branch locally
        module_logger().debug(
            "Found the following branches locally: \n %s..." % "\n".join([h.name for h in git_repo.heads])
        )
        head = git_repo.heads[branch_name]
        head.checkout()
        return head
    except IndexError as e:
        module_logger().debug("Branch name not in local repository! Checking origin...")
        for remote in git_repo.remotes:  # checkout branch remote and track
            try:
                module_logger().debug("Trying remote: %s..." % remote.name)
                head = remote.refs[branch_name].checkout("--track")
                return head
            except IndexError:
                module_logger().debug("Not found! Trying next...")
        module_logger().debug("Nothing left to try...")
        raise IndexError("Branch \"%s\" not in repository!" % branch_name) from e


def retrieve_files_from_head(head, pattern, option="", number_of_files=1):
    """Extracts a file with a "startswith" pattern given a branch (or head) of a repository.

    Args:
        number_of_files:
            The number of files to expect to be found when using the given pattern. Use -1 for arbitrary many.
        option:
            Specify "startswith" to do a prefix comparison instead of a regular expression matching
        head:
            The branch (or more general head) of the catalog repository where the solution file was committed in.
        pattern:
            The pattern the path of the file to retrieve should start with.

    Returns:
        The absolute path of the solution file (in the catalog repository).

    Raises:
        RuntimeError when
            a) there is no parent commit in the head
            b) No solution file is included in the latest commit of the given head
            c) There are more than a single solution file committed in the latest commit.

    """
    pattern = str(pattern)
    parent = head.commit.parents[0] if head.commit.parents else None
    module_logger().debug("Found head commit: %s..." % parent)
    module_logger().debug("Summary message: %s..." % parent.summary)

    if not parent:
        raise RuntimeError("Cannot execute diff since there is only a single commit!")

    diff = head.commit.diff(parent)

    abs_path_solution_file = []
    for file in diff:
        # unfortunately git on windows internally uses linux-separator as path separator.
        # Paths therefore might have the wrong separator.
        path = file.b_path.replace('/', os.path.sep)
        module_logger().debug("Found file in commit diff to parent: %s..." % path)
        module_logger().debug("Matching pattern %s..." % pattern)

        if option == "startswith":
            if path.startswith(pattern):
                module_logger().debug("Found file matching pattern %s: %s..." % (pattern, path))
                abs_path_solution_file.append(os.path.join(head.repo.working_tree_dir, path))
        else:
            if re.search(pattern, path):
                module_logger().debug("Found file matching pattern %s: %s..." % (pattern, path))
                abs_path_solution_file.append(os.path.join(head.repo.working_tree_dir, path))

    if not abs_path_solution_file:
        raise RuntimeError("Head \"%s\" does not hold pattern \"%s\"! Aborting..." % (head.name, pattern))

    if number_of_files > 0:
        if len(abs_path_solution_file) != number_of_files:
            raise RuntimeError(
                "Head \"%s\" holds pattern \"%s\" %s times, but expected %s. Aborting..." %
                (head.name, pattern, len(abs_path_solution_file), number_of_files)
            )

    return abs_path_solution_file


def _add_files(repo, file_paths) -> bool:
    """Add files to the repo in the branch currently checked out."""
    if repo.index.diff(None) or repo.untracked_files:
        module_logger().info('Preparing committing...')
        for file_path in file_paths:
            module_logger().debug('Adding file %s...' % file_path)
            # todo: nice catching here?
            repo.git.add(file_path)
        return True
    return False


def add_files_commit_and_push(head, file_paths, commit_message, push=False, email=None, username=None,
                              push_option_list=None, force=False):
    """Adds files in a given path to a git head and commits.

    Args:
        push_option_list:
            options used for pushing. See https://docs.gitlab.com/ee/user/project/push_options.html. Expects a list.
        head:
            The head of the repository
        file_paths:
            The path of the files to add
        commit_message:
            The commit message
        push:
            Boolean option to switch on/off pushing to repository remote
        username:
            The git user to use. (Default: systems git configuration)
        email:
            The git email to use. (Default: systems git configuration)
        force:
            whether to use force push or not

    Raises:
        RuntimeError when no files are in the index

    """
    if push_option_list is None or push_option_list == []:
        push_options = []
    else:
        push_options = ["-o %s" % o for o in push_option_list]

    repo = head.repo

    if email or username:
        configure_git(repo, email, username)

    if _add_files(repo, file_paths):

        # build command
        cmd_option = ['--set-upstream']
        cmd = cmd_option + push_options
        if force:
            cmd = cmd + ['-f']
        cmd = cmd + [repo.remote().refs.HEAD.remote_name, head]

        module_logger().debug("Running command: repo.git.push(%s)..." % (", ".join(str(x) for x in cmd)))

        # commit
        repo.git.commit(m=commit_message)

        try:
            if push:
                module_logger().info('Preparing pushing...')
                repo.git.push(cmd)

        except git.GitCommandError:
            raise
    else:
        raise RuntimeError("Diff shows no changes to the repository. Aborting...")


def configure_git(repo, email, username):
    """Configures email and username to use for git operations for the given repo.

    Args:
        repo:
            The repo to configure.
        email:
            The email to use.
        username:
            The username to use.

    Returns:
        repo:
            The configured repository.

    """
    if username:
        module_logger().info("Set username to \"%s\"" % username)
        repo.config_writer().set_value("user", "name", username).release()
    if email:
        module_logger().info("Set email to \"%s\"" % email)
        repo.config_writer().set_value("user", "email", email).release()
    if not username and not email:
        module_logger().warning("Neither username nor email given! Doing nothing...")

    return repo


# todo: write test
def create_new_head(repo, name):
    """Force creates a new head of a given name in a repository and returns the head."""

    if name in repo.heads:
        git.Head.delete(repo, name, force=True)
    new_head = repo.create_head(name)

    return new_head


def download_repository(repo_url, git_folder_path, force_download=True, update=True) -> Repo:
    """Downloads or updates the repository behind a url, returns repository object on success.

    If repository already cached, head is detached to origin HEAD for a clean start for new branches.

    Args:
        repo_url:
            The URL to the git.
        git_folder_path:
            The complete path to clone to
        force_download:
            Boolean, indicates whether to force delete existing folder before cloning
        update:
            Flag to indicate whether to hard reset the repo upon initialization or not.

    Returns:
        The repository object

    """
    git_folder_path = Path(git_folder_path)
    Path.mkdir(git_folder_path, parents=True, exist_ok=True)

    # update existing repo or clone new repo
    if Path.exists(git_folder_path.joinpath(".git")):
        module_logger().info("Found existing repository in %s..." % git_folder_path)

        if update:
            repo = init_repository(git_folder_path)
        else:
            repo = git.Repo(git_folder_path)
    else:

        if force_download:
            force_remove(git_folder_path)

        module_logger().info("Download repository from %s in %s..." % (repo_url, git_folder_path))
        repo = git.Repo.clone_from(repo_url, git_folder_path)

    return repo


def checkout_files(repo, files_to_download):
    for file in files_to_download:
        repo.git.restore(file, staged=True)
        repo.git.checkout(file)


@contextmanager
def clone_repository(repo_url, branch_name, target_repo_path) -> Generator[Repo, None, None]:
    git_folder_path = Path(target_repo_path)
    force_remove(git_folder_path)
    Path.mkdir(git_folder_path, parents=True, exist_ok=True)
    module_logger().debug("Cloning repository without history from %s into %s..." % (repo_url, git_folder_path))
    repo = git.Repo.clone_from(repo_url, git_folder_path, branch=branch_name, no_checkout=True, depth=1, no_tags=True,
                               single_branch=True)
    yield repo
    repo.close()


def init_repository(path):
    """Initializes a repository to the origin reference. Thereby discarding all changes made to the repository.

    Usually this means checking out the origin "main" branch, but this depends on the repository configuration.

    Args:
        path:
            The path to the repository to init/reset.

    Returns:
        the repository object.

    """
    module_logger().info("Initialize repository...")
    path = Path(path)

    repo = git.Repo(path)

    # update the remote to get latest changes on all remotes (pushes, HEAD pointer change, reverts, etc.)
    repo.remote().update()

    # remove all eventual changes made local
    clean_repository(repo)

    # checkout remote HEAD for a clean start for new branches
    repo.remote().refs.HEAD.checkout()

    return repo


def clean_repository(repo):
    """Resets all changes made in the current repository"""
    # reset to current remote HEAD reference name
    repo.git.reset(['--hard', repo.remote().refs.HEAD.ref.name])
    # remove all leftover-untracked files (if any)
    repo.git.clean('-fd')


def checkout_main(repo):
    """Checks out the main branch of the repository locally. Note: must not be called "main"!"""
    remote_main_name = repo.remote().refs.HEAD.ref.remote_head
    # checkout main or whatever its called the origin currently points to
    head = repo.heads[remote_main_name]
    head.checkout()

    return head


def retrieve_default_mr_push_options(repo_url) -> list:
    """Returns the default push option for the given repository host if available (e.g. gitlab, github)

    Args:
        repo_url:
            The source url of the catalog. Netloc determines default push option.

    Returns:
        The default push option to directly create a merge request when pushed to origin.

    """
    if is_url(repo_url):
        parsed_url = urlparse(repo_url)

        if parsed_url.netloc.startswith("gitlab"):
            return ["merge_request.create"]
        else:
            return []
    else:
        return []
