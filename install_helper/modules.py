import os
import git
from pathlib import Path

from xdg import xdg_data_dirs


def download_repository(hips_object):
    """Downloads the repository if needed, returns repository_path on success.

    Args:
        hips_object:
            The hips object.

    Returns:
        The directory of the git directory.

    Raises:
        GitCommandError: When there is an error with git.

    """
    # ToDo: discuss: which of the dataDirs to take - since it is a git do we need this extra folder `hips['name'}`?...
    download_path = xdg_data_dirs()[0].joinpath(hips_object['name'])
    Path.mkdir(download_path, parents=True, exist_ok=True)

    # update existing repo or clone new repo
    if Path.exists(download_path.joinpath(".git")):
        repo = git.Repo(download_path)
        try:
            repo.remote().fetch()
        except git.GitCommandError as err:
            print(err.stderr)
            print("Git command failed. Check your internet connection!")
            raise
        # checkout remote HEAD
        repo.remotes.origin.refs.HEAD.checkout()
        # remove all eventual changes made local to that commit
        repo.git.add('*')
        repo.git.reset('--hard')
    else:
        try:
            repo = git.Repo.clone_from(hips_object['git_repo'], download_path)
        except git.GitCommandError as err:
            print(err.stderr)
            raise

    # set the repository path
    hips_object["_repository_path"] = repo.working_tree_dir

    # set python workdir
    os.chdir(repo.working_tree_dir)

    return repo.working_tree_dir
