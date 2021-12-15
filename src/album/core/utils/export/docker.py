import pkgutil
from pathlib import Path

import album
from album.core.utils.operations.file_operations import copy_in_file
from album.core.utils.operations.resolve_operations import get_zip_name
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.solution import ISolution


def create_docker_file(active_solution: ISolution, target_folder: Path) -> Path:
    """Uses the template to create a docker file for the solution which gets deployed.

    Returns:
        The path to the docker file.
    """
    coordinates = active_solution.coordinates()
    zip_name = get_zip_name(coordinates)

    docker_file = target_folder.joinpath("Dockerfile")

    docker_file_stream = pkgutil.get_data('album.docker', 'Dockerfile_solution_template.txt').decode()

    docker_file_stream = docker_file_stream.replace("<version>", album.core.__version__)
    docker_file_stream = docker_file_stream.replace("<name>", zip_name)
    docker_file_stream = docker_file_stream.replace("<run_name>", str(coordinates))
    author = "; ".join(active_solution.setup().authors) if active_solution.setup().authors else "\"\""
    docker_file_stream = docker_file_stream.replace("<maintainer>", author)

    # replace template with entries and copy dockerfile to deploy_src
    get_active_logger().debug('Writing docker file to: %s...' % str(docker_file))
    copy_in_file(docker_file_stream, docker_file)

    return docker_file
