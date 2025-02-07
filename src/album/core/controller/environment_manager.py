import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from album.environments.api.environment_api import IEnvironmentAPI
from album.environments.api.model.environment import IEnvironment
from album.environments.initialization import init_environment_handler
from album.environments.model.environment import Environment
from album.environments.utils.file_operations import (
    get_dict_from_yml,
    write_dict_to_yml,
)

from album.core import __version__ as album_version
from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DEFAULT_SOLUTION_ENV_CONTENT, DefaultValues
from album.core.model.link import Link
from album.core.utils.operations.file_operations import (
    construct_cache_link_target,
    create_path_recursively,
    remove_link,
)
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import set_environment_paths
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class EnvironmentManager(IEnvironmentManager):
    def __init__(self, album: IAlbumController):
        # get installed package manager
        self.env_base_path = self._get_base_envs_path(album)
        self._album = album
        self._environment_handler = init_environment_handler(
            self.env_base_path, album.configuration().base_cache_path()
        )

    def _get_base_envs_path(self, album: IAlbumController) -> Path:
        return Path(album.configuration().lnk_path()).joinpath(
            DefaultValues.lnk_env_prefix.value
        )

    def install_environment(
        self, collection_solution: ICollectionSolution, allow_recursive: bool = False
    ) -> IEnvironment:
        environment = self._create_environment_for_solution(
            collection_solution, allow_recursive
        )
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def _create_environment_for_solution(
        self, collection_solution: ICollectionSolution, allow_recursive: bool = False
    ) -> IEnvironment:
        env_name = self.get_environment_name(
            collection_solution.coordinates(), collection_solution.catalog()
        )
        dependencies = collection_solution.loaded_solution().setup().dependencies
        cache = (
            collection_solution.loaded_solution().installation().internal_cache_path()
        )
        album_api_version = (
            collection_solution.loaded_solution().setup().album_api_version
        )
        solution_package_path = (
            collection_solution.loaded_solution().installation().package_path()
        )
        environment = self.create_environment(
            cache,
            dependencies,
            env_name,
            album_api_version,
            solution_package_path,
            allow_recursive,
        )
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def create_environment(
        self,
        cache: Path,
        dependencies: Dict[str, Any],
        env_name: str,
        album_api_version: str,
        solution_package_path: Path,
        allow_recursive: bool = False,
    ) -> IEnvironment:
        env_file = self._prepare_env_file(
            dependencies, cache, env_name, album_api_version, allow_recursive
        )
        env_path = self.get_environment_path(env_name, create=True)
        environment = Environment(env_file, env_name, env_path)
        solution_lock_file = solution_package_path.joinpath("solution.conda-lock.yml")
        self._environment_handler.create_environment_prefer_lock_file(
            environment, str(solution_lock_file.absolute())
        )

        return environment

    @staticmethod
    def _get_pypi_package_name_version(str_: str) -> Tuple[str, str]:
        if "==" in str_:
            p = str_.split("==")[0]
            v = str_.split("==")[-1]
        elif "~=" in str_:
            p = str_.split("~=")[0]
            v = str_.split("~=")[-1]
        else:
            p = str_
            v = ""
        return p, v

    def _check_album_in_album(
        self, yml_dict: Dict[str, Any], allow_recursive: bool = False
    ) -> None:
        album_installed_version = None
        if "dependencies" in yml_dict:
            for dep in yml_dict["dependencies"]:
                # check for pip dependencies
                if isinstance(dep, dict):
                    if "pip" in dep:
                        for pip_dep in dep["pip"]:
                            if (
                                "album"
                                == self._get_pypi_package_name_version(pip_dep)[0]
                            ):
                                album_installed_version = (
                                    self._get_pypi_package_name_version(pip_dep)[-1]
                                )
                                # check if unversioned
                                album_installed_version = (
                                    album_version
                                    if album_installed_version == ""
                                    else album_installed_version
                                )
                                break
                if isinstance(dep, str):
                    if "album" == dep.split("=")[0]:
                        album_installed_version = dep.split("=")[-1]
                        # check if unversioned
                        album_installed_version = (
                            album_version
                            if album_installed_version == "album"
                            else album_installed_version
                        )
                        break

        if album_installed_version == album_version:
            module_logger().warning(
                "Album is planned to be installed in the solution environment. "
                "This might cause issues when sharing the same database!"
                "Only proceed if you know what you are doing!"
            )
        if album_installed_version is not None and (
            album_installed_version != album_version
        ):
            str_ = (
                "Album is planned to be installed in the solution environment with a different version."
                " They might be incompatible! It is recommended to update the parent solution!"
                " If you know what you are doing, set allow_recursive during installation!"
            )
            if not allow_recursive:
                module_logger().error(str_)
                raise ValueError(str_)
            else:
                module_logger().info(
                    "Potentially incompatible installation of album in album detected!"
                )

    def set_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        db_entry = collection_solution.database_entry()

        if db_entry is None:
            raise ValueError("Database entry not set! Cannot resolve environment.")

        parent = db_entry.internal()["parent"]
        if not parent:
            env_name = self.get_environment_name(
                collection_solution.coordinates(), collection_solution.catalog()
            )
            environment = Environment(None, env_name, None)
            self.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            coordinates = dict_to_coordinates(parent.setup())
            catalog = self._album.catalogs().get_by_id(parent.internal()["catalog_id"])
            env_name = self.get_environment_name(coordinates, catalog)
            environment = Environment(None, env_name, None)
            self.set_environment_path(environment)

        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def _environment_name_to_path(
        self, environment_name: str, create: bool = True
    ) -> Optional[Link]:
        path = Path(
            os.path.normpath(
                self._album.configuration()
                .environments_path()
                .joinpath(environment_name)
            )
        )
        target = construct_cache_link_target(
            self._album.configuration().lnk_path(),
            point_from=path,
            point_to=Path(DefaultValues.lnk_env_prefix.value),
            create=create,
        )
        if target:
            return Link(target).set_link(path)
        else:
            return None

    def get_environment_path(
        self, environment_name: str, create: bool = True
    ) -> Optional[Link]:
        path_env = self._environment_name_to_path(environment_name, create)
        return path_env

    def get_installed_environment_path(self, environment_name: str) -> Link:
        path_expected = self._environment_name_to_path(environment_name, create=False)

        if path_expected is None:
            raise LookupError("Could not find environment %s." % environment_name)

        environment_list = (
            self._environment_handler.get_package_manager().get_environment_list()
        )

        if path_expected.resolve() in [env.resolve() for env in environment_list]:
            return path_expected

        raise LookupError("Could not find environment %s." % environment_name)

    def set_environment_path(self, environment: IEnvironment) -> None:
        path = self.get_environment_path(environment.name())
        module_logger().debug("Set environment path to %s..." % path)
        environment.set_path(path)

    def remove_environment(self, environment: IEnvironment) -> bool:
        self._environment_handler.remove_environment(environment)
        self.remove_disc_content_from_environment(environment)
        return True

    def run_script(
        self,
        environment: IEnvironment,
        script: str,
        environment_variables: Optional[
            Union[
                Mapping,
                None,
            ]
        ] = None,
        argv: Optional[List[str]] = None,
        pipe_output: bool = True,
    ) -> None:
        argv_ = argv if argv else []
        self._environment_handler.run_script(
            environment, script, environment_variables, argv_, pipe_output
        )

    @staticmethod
    def get_environment_name(coordinates: ICoordinates, catalog: ICatalog) -> str:
        return "_".join(
            [
                str(catalog.name()),
                coordinates.group(),
                coordinates.name(),
                coordinates.version(),
            ]
        )

    @staticmethod
    def remove_disc_content_from_environment(environment: IEnvironment) -> None:
        remove_link(environment.path())

    def _prepare_env_file(
        self,
        dependencies_dict: Dict[str, Any],
        cache_path: Path,
        env_name: str,
        album_api_version: Optional[str] = "",
        allow_recursive: bool = False,
    ) -> Path:
        yaml_path = cache_path.joinpath("{n}{s}".format(n=env_name, s=".yml"))
        create_path_recursively(yaml_path.parent)
        yaml_dict = None
        if dependencies_dict:
            if "environment_file" in dependencies_dict:
                env_file = dependencies_dict["environment_file"]

                self._album.resource_manager().handle_env_file_dependency(
                    env_file, yaml_path
                )

                yaml_dict = get_dict_from_yml(yaml_path)
                yaml_dict["name"] = env_name

        if not album_api_version:
            album_api_version = DefaultValues.runner_api_package_version.value

        if not yaml_dict:
            yaml_dict = deepcopy(DEFAULT_SOLUTION_ENV_CONTENT)

        # safety check to avoid album in album issues
        self._check_album_in_album(yaml_dict, allow_recursive)

        # package name
        runner_package_name = DefaultValues.runner_api_package_name.value

        # if specified, install the outdated runner
        if self._album.migration_manager().is_migration_needed_solution_api(
            album_api_version
        ):
            (
                runner_package_name,
                album_api_version,
            ) = (
                self._album.migration_manager().get_conda_available_outdated_runner_name_and_version()
            )

        yaml_dict = self._append_framework_to_dependencies(
            yaml_dict, album_api_version, runner_package_name
        )
        write_dict_to_yml(yaml_path, yaml_dict)

        return yaml_path

    def _append_framework_to_dependencies(
        self,
        content: Dict[str, Any],
        album_api_version: Optional[str],
        runner_package_name: str,
    ) -> Dict[str, Any]:
        if album_api_version is None:
            module_logger().warning("No framework specified for the environment.")
            # install no framework
            return content

        # Check if framework is properly defined. No zip, https or folder allowed.
        if (
            Path(DefaultValues.runner_api_package_name.value).is_dir()
            or DefaultValues.runner_api_package_name.value.endswith(".zip")
            or DefaultValues.runner_api_package_name.value.startswith("https")
        ):
            raise ValueError(
                "Framework is not properly defined. No zip, https or folder allowed."
            )

        return EnvironmentManager._append_framework_via_conda_to_yml(
            content, album_api_version, runner_package_name
        )

    @staticmethod
    def _append_framework_via_conda_to_yml(
        content: Dict[str, Any], album_api_version: str, runner_package_name: str
    ) -> Dict[str, Any]:
        framework = "conda-forge::{d}={a}".format(
            d=runner_package_name,
            a=album_api_version,
        )
        if "dependencies" not in content or not content["dependencies"]:
            content["dependencies"] = []
        content["dependencies"].append(framework)
        return content

    def get_environment_handler(self) -> IEnvironmentAPI:
        return self._environment_handler
