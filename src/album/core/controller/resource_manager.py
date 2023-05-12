import os
import subprocess
from io import StringIO
from pathlib import Path
from subprocess import SubprocessError

import validators
import yaml

from album.core.api.controller.resource_manager import IResourceManager
from album.core.api.controller.controller import IAlbumController
from album.core.api.model.catalog import ICatalog
from album.core.controller.conda_manager import CondaManager
from album.core.controller.package_manager import PackageManager
from album.core.model.default_values import DefaultValues
from album.core.utils.export.changelog import (
    create_changelog_file,
)
from album.core.utils.export.conda_lock import create_conda_lock_file
from album.core.utils.operations.file_operations import (
    copy,
    write_dict_to_yml,
)
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.core.utils.operations.url_operations import download_resource
from album.core.utils.subcommand import SubProcessError
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


class ResourceManager(IResourceManager):

    def __init__(self, album: IAlbumController):
        self.album = album

    def write_solution_files(
        self,
        catalog: ICatalog,
        catalog_local_src: str,
        active_solution: ISolution,
        deploy_path: Path,
        no_conda_lock: bool,
    ):
        coordinates = active_solution.coordinates()

        catalog_solution_local_src_path = Path(catalog_local_src).joinpath(
            self.album.configuration().get_solution_path_suffix_unversioned(coordinates)
        )

        res = []
        if deploy_path.is_file():
            solution_path = catalog_solution_local_src_path.joinpath(
                DefaultValues.solution_default_name.value
            )
            res.append(copy(deploy_path, solution_path))
        else:
            for subdir, dirs, files in os.walk(deploy_path):
                for file in files:
                    filepath = subdir + os.sep + file
                    rel_path = os.path.relpath(filepath, deploy_path)
                    target = catalog_solution_local_src_path.joinpath(rel_path)
                    res.append(copy(filepath, target))

        res.append(
            self._create_yaml_file_in_local_src(
                active_solution, catalog_solution_local_src_path
            )
        )
        res.append(
            create_changelog_file(
                active_solution, catalog, catalog_solution_local_src_path
            )
        )

        if not no_conda_lock:
            try:
                res.append(
                    create_conda_lock_file(self.write_solution_environment_file(active_solution,
                                                                                catalog_solution_local_src_path),
                                           self.album.configuration().conda_lock_executable())
                )
            except SubProcessError as e:
                module_logger().error("Error creating conda lock file. This is most likely the case, "
                                      "because on of your dependency is not available for every platform album "
                                      "demands. Try using the --no-conda-lock flag for skipping the conda lock file "
                                      "creation.")
                raise e
        return res

    def write_solution_environment_file(self, solution: ISolution, solution_home: Path):
        """Writes the environment file for the given solution to the given path."""
        yml_path = solution_home.joinpath('environment.yml')
        try:
            env_file = solution.setup()["dependencies"]["environment_file"]
        except KeyError:
            env_file = None
        if env_file:
            if isinstance(env_file, str):
                # 1 Link
                if validators.url(env_file):
                    download_resource(env_file, yml_path)

                # 2 string aus solution file
                elif "dependencies:" in env_file and "\n" in env_file:
                    with open(str(yml_path), "w+") as yml_file:
                        yml_file.writelines(env_file)
                # 3 existing env.yml
                elif Path(env_file).is_file() and Path(env_file).stat().st_size > 0:
                    copy(env_file, yml_path)
                else:
                    raise TypeError(
                        "environment_file must either contain the content of the environment file, "
                        "contain the url to a valid file or point to a file on the disk!"
                    )
            # String stream
            elif isinstance(env_file, StringIO):
                with open(str(yml_path), "w+") as f:
                    env_file.seek(0)  # make sure we start from the beginning
                    f.writelines(env_file.readlines())
            else:
                raise RuntimeError(
                    "Environment file specified, but format is unknown!"
                    " Don't know where to run solution!"
                )
        else:
            # No env file specified, build default solution env file
            write_dict_to_yml(yml_path, DefaultValues.default_solution_env_content.value)

        yml_dict = yaml.load(open(yml_path, "r"), Loader=yaml.FullLoader)
        yml_dict = PackageManager.append_framework_to_yml(yml_dict, solution.setup()['album_api_version'])
        yml_dict = self._append_setuptools_to_yml(yml_dict)
        write_dict_to_yml(yml_path, yml_dict)

        return yml_path

    @staticmethod
    def _create_yaml_file_in_local_src(active_solution: ISolution, solution_home: Path):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        yaml_path = solution_home.joinpath(
            DefaultValues.solution_yml_default_name.value
        )

        module_logger().debug("Writing yaml file to: %s..." % yaml_path)
        write_dict_to_yml(yaml_path, get_deploy_dict(active_solution))

        return yaml_path

    @staticmethod
    def _append_setuptools_to_yml(content):
        """Appends setuptools as dependency to the yml file. Needed since setuptools is not functional in the solution
        environment when conda-lock creates the solution environment."""
        dependencies = "conda-forge::setuptools>=59.7.0"  # Decided to use this version as minimum since it's the first setuptools version which needs at least python 3.7 like album does
        if not "dependencies" in content or not content["dependencies"]:
            content["dependencies"] = []
        if not 'setuptools' in content["dependencies"]:
            content["dependencies"].append(dependencies)
        return content

