from pathlib import Path

from album.core.utils import subcommand
from album.core.utils.operations.file_operations import force_remove


def create_conda_lock_file(solution_yml: Path, conda_lock_executable: Path):
    solution_lock_path = solution_yml.parent.joinpath("solution.conda-lock.yml")
    if solution_lock_path.exists():
        force_remove(solution_lock_path)
    conda_lock_args = [
        str(conda_lock_executable),
        "--file",
        str(solution_yml),
        "-p",
        "linux-64",
        "-p",
        "osx-64",
        "-p",
        "win-64",
        "-p",
        "osx-arm64",  # For Apple Silicon, e.g. M1/M2
        "-p",
        "linux-aarch64",  # aka arm64, use for Docker on Apple Silicon
        "-p",
        "linux-ppc64le",
        "--lockfile",
        str(solution_lock_path)]
    subcommand.run(conda_lock_args)
    return solution_lock_path
