import os
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Union

import validators
import yaml
from album.environments.utils.file_operations import write_dict_to_yml
from album.environments.utils.subcommand import SubProcessError
from album.environments.utils.url_operations import download_resource
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.resource_manager import IResourceManager
from album.core.api.model.catalog import ICatalog
from album.core.model.default_values import DEFAULT_SOLUTION_ENV_CONTENT, DefaultValues
from album.core.utils.export.changelog import create_changelog_file
from album.core.utils.operations.file_operations import copy
from album.core.utils.operations.solution_operations import get_deploy_dict

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
            # todo: replace me with copy_folder function
            for subdir, _, files in os.walk(deploy_path):
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
            c_lock_manager = (
                self.album.environment_manager()
                .get_environment_handler()
                .get_conda_lock_manager()
            )
            try:
                lock_path = c_lock_manager.create_conda_lock_file(
                    self.write_solution_environment_file(
                        active_solution, catalog_solution_local_src_path
                    ),
                    Path(c_lock_manager.conda_lock_executable()),
                )
                if lock_path:
                    res.append(lock_path)
            except SubProcessError as e:
                module_logger().error(
                    "Error creating conda lock file. This is most likely the case, "
                    "because on of your dependency is not available for every platform album "
                    "demands. Try using the --no-conda-lock flag for skipping the conda lock file "
                    "creation."
                )
                raise e
            except RuntimeError as e:
                module_logger().error(
                    "Cannot create conda lock file. No conda lock executable found. "
                    "Consider deploying without conda lock or install conda-lock!"
                )
                raise e
        return res

    def handle_env_file_dependency(
        self, env_file: Union[str, Dict[str, Any], StringIO], yml_path: Path
    ) -> None:
        if isinstance(env_file, str):
            self._handle_env_file_string(env_file, yml_path)
        elif isinstance(env_file, StringIO):
            self._handle_env_file_stream(env_file, yml_path)
        elif isinstance(env_file, dict):
            self._handle_env_file_dict(env_file, yml_path)
        else:
            raise TypeError(
                "environment_file must either contain the content of the environment file, "
                "contain the url to a valid file or point to a file on the disk!"
            )

    @staticmethod
    def _handle_env_file_string(env_file: str, yml_path: Path) -> None:
        # 1. Link
        if validators.url(env_file):
            download_resource(env_file, yml_path)
        # 2. string from solution file
        elif "dependencies:" in env_file and "\n" in env_file:
            with open(str(yml_path), "w+") as yml_file:
                yml_file.writelines(env_file)
        # 3. existing env.yml
        elif (
            Path(env_file).is_file()
            and Path(env_file).stat().st_size > 0
            and str(env_file).endswith(".yml")
        ):
            copy(env_file, yml_path)
        else:
            raise TypeError(
                "environment_file must either contain the content of the environment file, "
                "contain the url to a valid file or point to a file on the disk!"
            )

    @staticmethod
    def _handle_env_file_stream(env_file_stream: StringIO, yml_path: Path) -> None:
        with open(str(yml_path), "w+") as f:
            env_file_stream.seek(0)
            f.writelines(env_file_stream.readlines())

    @staticmethod
    def _handle_env_file_dict(env_file_dict: Dict[str, Any], yml_path: Path) -> None:
        write_dict_to_yml(yml_path, env_file_dict)

    def write_solution_environment_file(
        self, solution: ISolution, solution_home: Path
    ) -> Path:
        yml_path = solution_home.joinpath("environment.yml")
        try:
            env_file = solution.setup()["dependencies"]["environment_file"]
        except KeyError:
            env_file = None

        if env_file:
            self.handle_env_file_dependency(env_file, yml_path)
        else:
            # No env file specified, build default solution env file
            write_dict_to_yml(yml_path, deepcopy(DEFAULT_SOLUTION_ENV_CONTENT))
        with open(yml_path) as yml_file:
            yml_dict = yaml.load(yml_file, Loader=yaml.FullLoader)

        runner_package_name = DefaultValues.runner_api_package_name.value
        solution_api_version = solution.setup()["album_api_version"]

        # if the solution api version is outdated, we need to append the outdated runner. We always install the
        # first available conda-forge version of the outdated runner.
        if self.album.migration_manager().is_migration_needed_solution_api(
            solution_api_version
        ):
            (
                runner_package_name,
                solution_api_version,
            ) = (
                self.album.migration_manager().get_conda_available_outdated_runner_name_and_version()
            )

        yml_dict = self.album.environment_manager()._append_framework_to_dependencies(
            yml_dict, solution_api_version, runner_package_name
        )
        yml_dict = self._append_setuptools_to_yml(yml_dict)
        write_dict_to_yml(yml_path, yml_dict)

        return yml_path

    @staticmethod
    def _create_yaml_file_in_local_src(
        active_solution: ISolution, solution_home: Path
    ) -> Path:
        yaml_path = solution_home.joinpath(
            DefaultValues.solution_yml_default_name.value
        )

        module_logger().debug("Writing yaml file to: %s..." % yaml_path)
        write_dict_to_yml(yaml_path, get_deploy_dict(active_solution))

        return yaml_path

    @staticmethod
    def _append_setuptools_to_yml(content: Dict[str, Any]) -> Dict[str, Any]:
        # Decided to use this version as minimum since it's the first setuptools version which needs at least
        # python 3.7 like album does.
        dependencies = "conda-forge::setuptools>=59.7.0"
        if "dependencies" not in content or not content["dependencies"]:
            content["dependencies"] = []
        if "setuptools" not in content["dependencies"]:
            content["dependencies"].append(dependencies)
        return content
