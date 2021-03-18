import os
import shutil
from pathlib import Path

import git

from utils import hips_logging

module_logger = hips_logging.get_active_logger


def _checkout_branch(git_repo_path, branch_name):
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
        module_logger().debug("Found the following branches locally: \n %s " % "\n".join([h.name for h in repo.heads]))
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


def _retrieve_single_file_from_head(head, pattern):
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
    module_logger().debug("Found head commit: %s" % parent)
    module_logger().debug("Summary message: %s" % parent.summary)

    if not parent:
        raise RuntimeError("Cannot execute diff since there is only a single commit!")

    diff = head.commit.diff(parent)

    abs_path_solution_file = []
    for file in diff:
        module_logger().debug("Found file in commit diff to parent: %s " % file.a_path)
        if file.a_path.startswith(pattern):
            module_logger().debug("Found file matching pattern %s: %s " % (pattern, file.a_path))
            abs_path_solution_file.append(os.path.join(head.repo.working_tree_dir, file.a_path))

    if not abs_path_solution_file:
        raise RuntimeError("Illegal merge request! Pattern not found! Aborting...")
    if len(abs_path_solution_file) > 1:
        raise RuntimeError("Illegal merge request! Pattern found too many times! Aborting...")

    return abs_path_solution_file[0]


def _add_files_commit_and_push(head, file_paths, commit_message, dry_run=False, trigger_pipeline=True):
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

    Raises:
        RuntimeError when no files are in the index

    """
    repo = head.repo

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


# todo: make non private and test
def __create_new_head(repo, name):
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
    Path.mkdir(git_folder_path, parents=True, exist_ok=True)

    # update existing repo or clone new repo
    if Path.exists(git_folder_path.joinpath(".git")):
        module_logger().info("Found existing repository in %s. Trying to update." % git_folder_path)

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
