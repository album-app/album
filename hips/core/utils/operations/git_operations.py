import os
from pathlib import Path

import git

from hips_runner import logging

module_logger = logging.get_active_logger


def checkout_branch(git_repo_path, branch_name):
    """Checks out a branch on a repository.

    First, local refs are taken, then refs pointing to origin.

    Args:
        git_repo_path:
            The path to a repository
        branch_name:
            The name of the branch to check out

    Returns:
        The head of the branch

    Raises:
        IndexError when the branch is no where available.

    """
    repo = git.Repo(git_repo_path)
    module_logger().debug("Repository found in %s..." % git_repo_path)

    try:  # checkout branch locally
        module_logger().debug("Found the following branches locally: \n %s..." % "\n".join([h.name for h in repo.heads]))
        head = repo.heads[branch_name]
        return head
    except IndexError as e:
        module_logger().debug("Branch name not in local repository! Checking origin...")
        for remote in repo.remotes:  # checkout branch remote and track
            try:
                module_logger().debug("Trying remote: %s..." % remote.name)
                head = remote.refs[branch_name].checkout("--track")
                return head
            except IndexError:
                module_logger().debug("Not found! Trying next...")
        module_logger().debug("Nothing left to try...")
        raise IndexError("Branch %s not in repository!" % branch_name) from e


def retrieve_single_file_from_head(head, pattern):
    """Extracts a file with a "startswith" pattern given a branch (or head) of a repository.

    Args:
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
        if path.startswith(pattern):
            module_logger().debug("Found file matching pattern %s: %s..." % (pattern, path))
            abs_path_solution_file.append(os.path.join(head.repo.working_tree_dir, path))

    if not abs_path_solution_file:
        raise RuntimeError("Illegal merge request! Pattern not found! Aborting...")
    if len(abs_path_solution_file) > 1:
        raise RuntimeError("Illegal merge request! Pattern found too many times! Aborting...")

    return abs_path_solution_file[0]


def add_files_commit_and_push(head, file_paths, commit_message, dry_run=False, trigger_pipeline=True,
                              email=None, username=None):
    """Adds files in a given path to a git head and commits.

    Args:
        head:
            The head of the repository
        file_paths:
            The path of the files to add
        commit_message:
            The commit message
        dry_run:
            Boolean option to switch on dry-run, not doing actual pushing
        trigger_pipeline:
            Boolean option to switch on pipeline triggering after pushing
        username:
            The git user to use. (Default: systems git configuration)
        email:
            The git email to use. (Default: systems git configuration)

    Raises:
        RuntimeError when no files are in the index

    """
    repo = head.repo

    if email or username:
        configure_git(repo, email, username)

    if repo.index.diff() or repo.untracked_files:
        module_logger().info('Creating a merge request...')

        for file_path in file_paths:
            module_logger().debug('Adding file %s...' % file_path)
            # todo: nice catching here?
            repo.git.add(file_path)

        repo.git.commit(m=commit_message)

        try:  # see https://docs.gitlab.com/ee/user/project/push_options.html
            cmd_option = ['--set-upstream']

            if not trigger_pipeline:
                cmd_push_option = ['--push-option=ci.skip']
            else:
                cmd_push_option = ['--push-option=merge_request.create']

            cmd = cmd_option + cmd_push_option + ['-f', 'origin', head]

            module_logger().debug("Running command: repo.git.push(%s)..." % (", ".join(str(x) for x in cmd)))
            if not dry_run:
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
        repo.config_writer().set_value("user", "name", username).release()
    if email:
        repo.config_writer().set_value("user", "email", email).release()

    return repo


# todo: write test
def create_new_head(repo, name):
    """Force creates a new head of a given name in a repository and returns the head."""

    if name in repo.heads:
        git.Head.delete(repo, name, force=True)
    new_head = repo.create_head(name)

    return new_head


def download_repository(repo_url, git_folder_path):
    """Downloads or updates the repository behind a url, returns repository object on success.

    If repository already cached, head is detached to origin HEAD for a clean start for new branches.

    Args:
        repo_url:
            The URL to the git.
        git_folder_path:
            The complete path to clone to

    Returns:
        The repository object

    """
    git_folder_path = Path(git_folder_path)
    Path.mkdir(git_folder_path, parents=True, exist_ok=True)

    # update existing repo or clone new repo
    if Path.exists(git_folder_path.joinpath(".git")):
        module_logger().info("Found existing repository in %s. Trying to update..." % git_folder_path)

        repo = git.Repo(git_folder_path)

        # remove all eventual changes made local
        repo.git.add('*')
        repo.git.reset('--hard')

        # update the remote
        repo.remote().update()

        # checkout remote HEAD for a clean start for new branches
        repo.remote().refs.HEAD.checkout()

    else:
        module_logger().info("Download repository from %s in %s..." % (repo_url, git_folder_path))
        repo = git.Repo.clone_from(repo_url, git_folder_path)

    return repo
