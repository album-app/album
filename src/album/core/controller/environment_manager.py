from io import StringIO
from pathlib import Path

import validators
from packaging import version

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.environment import IEnvironment
from album.core.controller.conda_lock_manager import CondaLockManager
from album.core.controller.conda_manager import CondaManager
from album.core.controller.mamba_manager import MambaManager
from album.core.controller.micromamba_manager import MicromambaManager
from album.core.model.default_values import DefaultValues
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import (
    remove_link,
    copy,
    get_dict_from_yml,
    write_dict_to_yml,
    create_path_recursively,
)
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.core.utils.operations.solution_operations import set_environment_paths
from album.core.utils.operations.url_operations import download_resource
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class EnvironmentManager(IEnvironmentManager):
    def __init__(self, album: IAlbumController):
        if album.configuration().micromamba_executable():
            self._package_manager = MicromambaManager(album.configuration())
            self._env_install_manager = self._package_manager
        else:
            self._package_manager = CondaManager(album.configuration())
            if album.configuration().mamba_executable():
                self._env_install_manager = MambaManager(album.configuration())
            else:
                self._env_install_manager = self._package_manager
        self._album = album
        self._conda_lock_manager = CondaLockManager(album.configuration())

    def install_environment(
        self, collection_solution: ICollectionSolution
    ) -> IEnvironment:
        environment = self.create_environment_for_solution(collection_solution)
        self._env_install_manager.install(environment)
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def create_environment_for_solution(self, collection_solution):
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
        set_environment_paths(collection_solution, environment)
        return environment

    def create_environment(self, cache, dependencies, env_name, album_api_version, solution_package_path):
        env_file = self._prepare_env_file(
            env_name, dependencies, cache, album_api_version
        )
        environment = Environment(env_file, env_name)
        solution_lock_file = solution_package_path.joinpath('solution.conda-lock.yml')
        if solution_lock_file.is_file():
            module_logger().debug("Creating solution environment from lock file.")
            self._conda_lock_manager.install(
                environment, album_api_version, solution_lock_file
            )
        else:
            self._env_install_manager.install(
                environment, album_api_version
            )
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
            environment = self.create_environment(cache_path, None, env_name, None)
            self._package_manager.set_environment_path(environment)

        # solution runs in the parents environment - we need to resolve first to get info about parents environment
        else:
            coordinates = dict_to_coordinates(parent.setup())
            catalog = self._album.catalogs().get_by_id(parent.internal()["catalog_id"])
            env_name = self.get_environment_name(coordinates, catalog)
            environment = self.create_environment(cache_path, None, env_name, None)
            self._package_manager.set_environment_path(environment)

        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def remove_environment(self, environment: IEnvironment) -> bool:
        """Removes an environment."""
        res = self._package_manager.remove_environment(environment.name())
        self.remove_disc_content_from_environment(environment)
        return res

    def run_script(
        self,
        environment: IEnvironment,
        script,
        environment_variables=None,
        argv=None,
        pipe_output=True,
    ):
        if environment:
            self._package_manager.run_script(
                environment,
                script,
                environment_variables=environment_variables,
                argv=argv,
                pipe_output=pipe_output,
            )
        else:
            raise EnvironmentError("Environment not set! Cannot run scripts!")

    def get_package_manager(self):
        return self._package_manager

    def get_conda_lock_manager(self):
        return self._conda_lock_manager

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
                DefaultValues.runner_api_packet_name.value,
                album_api_version,
            )
        else:
            framework = "conda-forge::%s" % DefaultValues.runner_api_packet_name.value
        if not "dependencies" in content or not content["dependencies"]:
            content["dependencies"] = []
        content["dependencies"].append(framework)
        return content
