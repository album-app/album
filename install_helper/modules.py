import os
import git
from pathlib import Path

from xdg import xdg_data_dirs


def download_repository(repo_url, git_folder_name):
    """Downloads or updates the repository behind a url, returns repository_path on success.

    Args:
        repo_url:
            The URL to the git.
        git_folder_name:
            The folder name of the repository

    Returns:
        The repository object

    Raises:
        GitCommandError: When there is an error with gitpython.
    """
    download_path = xdg_data_dirs()[0].joinpath(git_folder_name)
    Path.mkdir(download_path, parents=True, exist_ok=True)

    # update existing repo or clone new repo
    if Path.exists(download_path.joinpath(".git")):
        print("Found existing repository in %s. Trying to update." % download_path)

        repo = git.Repo(download_path)
        # checkout remote HEAD
        repo.remotes.origin.refs.HEAD.checkout()
        # remove all eventual changes made local to that commit
        repo.git.add('*')
        repo.git.reset('--hard')
    else:
        print("Download repository from %s in %s..." % (repo_url, download_path))

        try:
            repo = git.Repo.clone_from(repo_url, download_path)
        except git.GitCommandError as err:
            print(err.stderr)
            raise

    return repo


def download_hips_repository(hips_object):
    """Downloads the repository specified in a hips object, returns repository_path on success.

    Additionally changes pythons working directory to the repository_path.

    Args:
        hips_object:
            The hips object.

    Returns:
        The directory of the git directory.

    Raises:
        GitCommandError: When there is an error with gitpython.
    """
    repo = download_repository(hips_object['git_repo'], hips_object['name'])

    repository_path = repo.working_tree_dir

    # set the repository path
    hips_object["_repository_path"] = repository_path

    # set python workdir
    os.chdir(repository_path)

    return repository_path
