import os
from io import StringIO
from pathlib import Path

import validators
from album.core.model.link import Link
from packaging import version

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import (
    remove_link,
    create_path_recursively, construct_cache_link_target,
)
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import set_environment_paths
from album.environments.api.model.environment import IEnvironment
from album.environments.initialization import init_environment_handler
from album.environments.model.environment import Environment
from album.environments.utils.file_operations import (
    get_dict_from_yml,
    write_dict_to_yml,
    copy,
)
from album.environments.utils.url_operations import download_resource
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class EnvironmentManager(IEnvironmentManager):
    def __init__(self, album: IAlbumController):
        # get installed package manager
        self.env_base_path = self._get_base_envs_path(album)
        self._album = album

        micromamba_path = DefaultValues.micromamba_path.value
        mamba_path = DefaultValues.mamba_path.value
        conda_path = DefaultValues.conda_path.value
        conda_lock_path = DefaultValues.conda_lock_path.value

        self.environment_handler = init_environment_handler(self.env_base_path, micromamba_path=micromamba_path, mamba_path=mamba_path, conda_path=conda_path, conda_lock_path=conda_lock_path)

    def _get_base_envs_path(self, album):
        return Path(album.configuration().lnk_path()).joinpath(
            DefaultValues.lnk_env_prefix.value
        )

    def install_environment(
        self, collection_solution: ICollectionSolution
    ) -> IEnvironment:
        environment = self._create_environment_for_solution(collection_solution)
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def _create_environment_for_solution(self, collection_solution):
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
        solution_package_path = collection_solution.loaded_solution().installation().package_path()
        environment = self.create_environment(cache, dependencies, env_name, album_api_version, solution_package_path)
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def create_environment(self, cache, dependencies, env_name, album_api_version, solution_package_path):
        env_file = self._prepare_env_file(dependencies, cache, env_name, album_api_version)
        env_path = self.get_environment_path(env_name, create=True).absolute()
        environment = Environment(env_file, env_name, env_path)
        solution_lock_file = solution_package_path.joinpath('solution.conda-lock.yml')
        self.environment_handler.create_environment_prefer_lock_file(environment, str(solution_lock_file.absolute()))
        return environment

    def set_environment(self, collection_solution: ICollectionSolution) -> IEnvironment:
        parent = collection_solution.database_entry().internal()["parent"]
        # solution runs in its own environment
        cache_path = (
            collection_solution.loaded_solution().installation().internal_cache_path()
        )
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

    def _environment_name_to_path(self, environment_name, create=True):
        path = os.path.normpath(
            self._album.configuration().environments_path().joinpath(environment_name)
        )
        target = construct_cache_link_target(
            self._album.configuration().lnk_path(),
            point_from=path,
            point_to=DefaultValues.lnk_env_prefix.value,
            create=create,
        )
        if target:
            return Link(target).set_link(path)
        else:
            return None

    def get_environment_path(self, environment_name: str, create: bool = True) -> Link:
        """Gets the environment path for a given environment

        Args:
            environment_name:
                The environment to get the path for.
            create:



        Returns:
            None or the path
        """
        path_expected = self._environment_name_to_path(environment_name, create)
        environment_list = self.environment_handler.get_package_manager().get_environment_list()

        if path_expected.resolve() in [env.resolve() for env in environment_list]:
            return path_expected
        raise LookupError("Could not find environment %s." % environment_name)

    def set_environment_path(self, environment: IEnvironment):
        path = self.get_environment_path(environment.name())
        module_logger().debug("Set environment path to %s..." % path)
        environment.set_path(path)

    def remove_environment(self, environment: IEnvironment) -> bool:
        self.environment_handler.remove_environment(environment)
        self.remove_disc_content_from_environment(environment)
        return True

    def run_script(
        self,
        environment: IEnvironment,
        script,
        environment_variables=None,
        argv=None,
        pipe_output=True,
    ):
        self.environment_handler.run_script(
            environment, script, environment_variables, argv, pipe_output
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
    def remove_disc_content_from_environment(environment: IEnvironment):
        remove_link(environment.path())

    @staticmethod
    def _prepare_env_file(dependencies_dict, cache_path, env_name, album_api_version):
        """Checks how to set up an environment. Returns a path to a valid yaml file. Environment name in that file
        will be overwritten!

        Args:
            dependencies_dict:
                Dictionary holding the "environment_file" key. Environment file can be:
                    - url
                    - path
                    - stream object

        Returns:
            Path to a valid yaml file where environment name has been replaced!

        """
        if dependencies_dict:
            if "environment_file" in dependencies_dict:
                env_file = dependencies_dict["environment_file"]

                yaml_path = cache_path.joinpath("%s%s" % (env_name, ".yml"))
                create_path_recursively(yaml_path.parent)

                if isinstance(env_file, str):
                    # case valid url
                    if validators.url(env_file):
                        yaml_path = download_resource(env_file, yaml_path)
                    # case file content
                    elif "dependencies:" in env_file and "\n" in env_file:
                        with open(str(yaml_path), "w+") as f:
                            f.writelines(env_file)
                        yaml_path = yaml_path
                    # case Path
                    elif Path(env_file).is_file() and Path(env_file).stat().st_size > 0:
                        yaml_path = copy(env_file, yaml_path)
                    else:
                        raise TypeError(
                            "environment_file must either contain the content of the environment file, "
                            "contain the url to a valid file or point to a file on the disk!"
                        )
                # case String stream
                elif isinstance(env_file, StringIO):
                    with open(str(yaml_path), "w+") as f:
                        env_file.seek(0)  # make sure we start from the beginning
                        f.writelines(env_file.readlines())
                    yaml_path = yaml_path
                else:
                    raise RuntimeError(
                        "Environment file specified, but format is unknown!"
                        " Don't know where to run solution!"
                    )

                yaml_dict = get_dict_from_yml(yaml_path)
                yaml_dict["name"] = env_name
                if not album_api_version:
                    album_api_version = DefaultValues.runner_api_package_version.value
                yaml_dict = EnvironmentManager._append_framework_to_dependencies(
                    yaml_dict, album_api_version
                )
                write_dict_to_yml(yaml_path, yaml_dict)

                return yaml_path
            return None
        return None

    @staticmethod
    def _append_framework_to_dependencies(content, album_api_version):
        if (
            not (
                Path(DefaultValues.runner_api_package_name.value).is_dir()
                or DefaultValues.runner_api_package_name.value.endswith(".zip")
                or DefaultValues.runner_api_package_name.value.startswith("https")
            )
            and album_api_version
            and version.parse(album_api_version)
            >= version.parse(DefaultValues.first_album_solution_api_version.value)
        ):
            return EnvironmentManager._append_framework_via_conda_to_yml(
                content, album_api_version
            )
        else:
            return EnvironmentManager._append_framework_via_conda_to_yml(
                content, DefaultValues.first_album_solution_api_version.value
            )

    @staticmethod
    def _append_framework_via_conda_to_yml(content, album_api_version):
        if album_api_version:
            framework = "conda-forge::%s=%s" % (
                DefaultValues.runner_api_package_name.value,
                album_api_version,
            )
        else:
            framework = "conda-forge::%s" % DefaultValues.runner_api_packet_name.value
        if not "dependencies" in content or not content["dependencies"]:
            content["dependencies"] = []
        content["dependencies"].append(framework)
        return content

    def get_environment_handler(self):
        return self.environment_handler
