import os
from pathlib import Path

from hips.core.model.configuration import HipsConfiguration

from hips.core.model import logging

from hips.core.utils import subcommand

module_logger = logging.get_active_logger


# todo: write test
def chdir_repository(active_hips):
    """Actively changes pythons working directory to the cache path of the solution.

    Args:
        active_hips:
            The HIP-solution class object.

    """
    configuration = HipsConfiguration()
    repo_path = configuration.get_cache_path_hips(active_hips).joinpath(active_hips["name"])

    # assumes repo is up to date!
    if repo_path.joinpath(".git").exists():
        os.chdir(str(repo_path))
    else:
        raise FileNotFoundError("Could not identify %s as repository. Aborting..." % repo_path)


# todo: write test
def run_as_executable(cmd, args):
    """Runs a solution as executable. Thereby only calling a command on the commandline within the correct environment.

    Args:
        cmd:
            The command to run.
        args:
            The arguments to the command.

    """
    from hips.core import get_active_hips
    from hips.core.model.environment import set_environment_name, set_environment_path

    active_hips = get_active_hips()
    set_environment_name(active_hips)
    environment_path = Path(set_environment_path(active_hips))

    executable_path = environment_path.joinpath("bin", cmd)
    cmd = [
        str(executable_path)
    ] + args

    subcommand.run(cmd)