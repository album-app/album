import os
import git
from pathlib import Path

from xdg import xdg_data_dirs


def download_repository(hips_object):
    """
    Downloads the repository if needed, returns repository_path on success
    """
    # ToDo: discuss: which of the dataDirs to take - since it is a git do we need this extra folder `hips['name'}`?...
    download_path = xdg_data_dirs()[0].joinpath(hips_object['name'])
    Path.mkdir(download_path, parents=True, exist_ok=True)

    # update existing repo or clone new repo
    if Path.exists(download_path.joinpath(".git")):  # ToDo: better checking here
        repo = git.Repo(download_path)
        try:
            repo.remote().fetch()
        except AssertionError as err:
            print(err)
            pass
        git.refs.head.HEAD(repo, path='HEAD').reset(commit='HEAD', index=True, working_tree=False)
    else:
        try:
            repo = git.Repo.clone_from(hips_object['git_repo'], download_path)
        except Exception as e:  # ToDo: to broad exception. Better error handling here
            print(e)
            return

    # set the repository path
    hips_object["_repository_path"] = repo.working_tree_dir

    # set python workdir
    os.chdir(repo.working_tree_dir)

    return repo.working_tree_dir
