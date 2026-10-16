import os
import re
from copy import deepcopy
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Union

import validators
import yaml

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.resource_manager import IResourceManager
from album.core.api.model.catalog import ICatalog
from album.core.model.default_values import DEFAULT_SOLUTION_ENV_CONTENT, DefaultValues
from album.core.utils.export.changelog import (
    create_changelog_file,
    get_changelog_file_name,
)
from album.core.utils.operations.file_operations import copy
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.environments.utils.file_operations import write_dict_to_yml
from album.environments.utils.subcommand import SubProcessError
from album.environments.utils.url_operations import download_resource
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger

# A conda dependency naming the setuptools package: "setuptools", optionally behind a
# channel ("conda-forge::setuptools") and followed by a version constraint
# ("setuptools>=60", "setuptools=70.*", "setuptools 70.*", "setuptools[version='>=60']").
# Other packages starting with the same letters, like "setuptools-scm", do not match.
_SETUPTOOLS_SPEC = re.compile(r"^(?:\S+::)?setuptools(?:$|[\s=<>!~\[])")

# The files a solution can name in its dependencies, with the text that marks their content.
_FILE_DEPENDENCIES = {
    "environment_file": "dependencies:",
    "resource_file": "resources:",
}


def _is_deployed(name: str) -> bool:
    """Tell whether a file or folder in the folder of a solution is deployed with it.

    Hidden files and folders (.git, .DS_Store, .ipynb_checkpoints, ...) and Python caches
    are not part of the solution.
    """
    return not name.startswith(".") and name != "__pycache__"


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
            skipped = []
            for subdir, dirs, files in os.walk(deploy_path):
                for name in dirs + files:
                    if not _is_deployed(name):
                        skipped.append(
                            os.path.relpath(os.path.join(subdir, name), deploy_path)
                        )
                # os.walk does not descend into the folders removed here
                dirs[:] = [d for d in dirs if _is_deployed(d)]
                for file in filter(_is_deployed, files):
                    filepath = subdir + os.sep + file
                    rel_path = os.path.relpath(filepath, deploy_path)
                    target = catalog_solution_local_src_path.joinpath(rel_path)
                    res.append(copy(filepath, target))
            if skipped:
                module_logger().info(
                    "Not deploying hidden files and folders and Python caches: %s"
                    % ", ".join(sorted(skipped))
                )

        res.append(
            self._create_yaml_file_in_local_src(
                active_solution, catalog_solution_local_src_path
            )
        )

        # Only generate a CHANGELOG.md when the user's deploy path did not
        # already provide one.  If the deploy_path was a directory containing
        # a CHANGELOG.md, the os.walk copy above already placed it in the
        # target and its path is already in ``res``.
        changelog_target = catalog_solution_local_src_path.joinpath(
            get_changelog_file_name()
        )
        if not changelog_target.exists():
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
            # conda-lock locks the environment album installs, the one of the solution with
            # album-solution-api added. It is written to a folder of its own, not to the
            # deployed files: the solution might come with an environment.yml itself.
            with TemporaryDirectory(
                dir=self.album.configuration().tmp_path()
            ) as tmp_dir:
                try:
                    lock_path = c_lock_manager.create_conda_lock_file(
                        self.write_solution_environment_file(
                            active_solution,
                            Path(tmp_dir),
                            deploy_path if deploy_path.is_dir() else None,
                        ),
                        Path(c_lock_manager.conda_lock_executable()),
                    )
                    if lock_path:
                        res.append(
                            copy(
                                lock_path,
                                catalog_solution_local_src_path.joinpath(
                                    Path(lock_path).name
                                ),
                            )
                        )
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

    def check_file_dependencies(
        self,
        solution: ISolution,
        solution_folder: Optional[Path],
        dependencies: Optional[List[str]] = None,
    ) -> None:
        setup_dependencies = solution.setup().dependencies or {}
        for dependency in dependencies or list(_FILE_DEPENDENCIES):
            file_dependency = setup_dependencies.get(dependency)
            if isinstance(file_dependency, str) and self._is_path(file_dependency):
                self._get_file(file_dependency, solution_folder, dependency)

    def handle_env_file_dependency(
        self,
        env_file: Union[str, Dict[str, Any], StringIO],
        yml_path: Path,
        solution_folder: Optional[Path] = None,
    ) -> None:
        self._handle_file_dependency(
            env_file, yml_path, "environment_file", solution_folder
        )

    def handle_resource_file_dependency(
        self,
        resource_file: Union[str, Dict[str, Any], StringIO],
        yml_path: Path,
        solution_folder: Optional[Path] = None,
    ) -> None:
        self._handle_file_dependency(
            resource_file, yml_path, "resource_file", solution_folder
        )

    def _handle_file_dependency(
        self,
        file_dependency: Union[str, Dict[str, Any], StringIO],
        yml_path: Path,
        dependency: str,
        solution_folder: Optional[Path],
    ) -> None:
        if isinstance(file_dependency, str):
            self._handle_env_file_string(
                file_dependency,
                yml_path,
                dependency,
                _FILE_DEPENDENCIES[dependency],
                solution_folder,
            )
        elif isinstance(file_dependency, StringIO):
            self._handle_env_file_stream(file_dependency, yml_path)
        elif isinstance(file_dependency, dict):
            self._handle_env_file_dict(file_dependency, yml_path)
        else:
            raise TypeError(self._invalid_file_dependency_message(dependency))

    @staticmethod
    def _handle_env_file_string(
        env_file: str,
        yml_path: Path,
        dependency: str = "environment_file",
        content_marker: str = "dependencies:",
        solution_folder: Optional[Path] = None,
    ) -> None:
        """Write a file dependency given as a string to yml_path. Used for the environment and the resource file."""
        # 1. Link
        if validators.url(env_file):
            download_resource(env_file, yml_path)
        # 2. string from solution file
        elif content_marker in env_file and "\n" in env_file:
            with open(str(yml_path), "w+", encoding="utf-8") as yml_file:
                yml_file.writelines(env_file)
        # 3. a file, a relative path starts at the folder of the solution
        elif ResourceManager._is_path(env_file):
            copy(
                ResourceManager._get_file(env_file, solution_folder, dependency),
                yml_path,
            )
        else:
            raise TypeError(
                ResourceManager._invalid_file_dependency_message(dependency)
            )

    @staticmethod
    def _is_path(file_dependency: str) -> bool:
        """Tell whether a file dependency given as a string is a path, neither a url nor content."""
        return "\n" not in file_dependency and not validators.url(file_dependency)

    @staticmethod
    def _get_file(file: str, solution_folder: Optional[Path], dependency: str) -> Path:
        """Find a file the solution names by its path.

        A relative path starts at solution_folder, the folder of the solution. A solution
        given as a single file, solution_folder None, has no folder: naming a file by a
        relative path makes it a solution that is installed and deployed as a folder.
        """
        path = Path(file)
        if not path.is_absolute():
            if solution_folder is None:
                raise TypeError(
                    f'{dependency} "{file}" is a path, so the solution has to be installed '
                    "and deployed as a folder: give the folder that holds solution.py and "
                    f'"{file}", not solution.py alone.'
                )
            path = solution_folder.joinpath(path)
        if not path.is_file():
            problem = (
                "does not exist."
                if path == Path(file)
                else f"does not exist: there is no file {path}."
            )
        elif not file.endswith((".yml", ".yaml")):
            problem = "is not a .yml or .yaml file."
        elif path.stat().st_size == 0:
            problem = "is empty."
        else:
            return path
        raise TypeError(f'{dependency} "{file}" {problem}')

    @staticmethod
    def _invalid_file_dependency_message(dependency: str) -> str:
        return (
            "%s must either contain the content of the %s, "
            "contain the url to a valid file or the path of a .yml file!"
            % (dependency, dependency.replace("_", " "))
        )

    @staticmethod
    def _handle_env_file_stream(env_file_stream: StringIO, yml_path: Path) -> None:
        with open(str(yml_path), "w+", encoding="utf-8") as f:
            env_file_stream.seek(0)
            f.writelines(env_file_stream.readlines())

    @staticmethod
    def _handle_env_file_dict(env_file_dict: Dict[str, Any], yml_path: Path) -> None:
        write_dict_to_yml(yml_path, env_file_dict)

    def write_solution_environment_file(
        self,
        solution: ISolution,
        solution_home: Path,
        solution_folder: Optional[Path] = None,
    ) -> Path:
        yml_path = solution_home.joinpath("environment.yml")
        try:
            env_file = solution.setup()["dependencies"]["environment_file"]
        except KeyError:
            env_file = None

        if env_file:
            self.handle_env_file_dependency(env_file, yml_path, solution_folder)
        else:
            # No env file specified, build default solution env file
            write_dict_to_yml(yml_path, deepcopy(DEFAULT_SOLUTION_ENV_CONTENT))
        with open(yml_path, encoding="utf-8") as yml_file:
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
        # Keep a setuptools spec the solution already declares. conda-lock keeps only
        # the last spec per package, so an appended pin would silently replace it.
        if not any(
            ResourceManager._is_setuptools_spec(dependency)
            for dependency in content["dependencies"]
        ):
            content["dependencies"].append(dependencies)
        return content

    @staticmethod
    def _is_setuptools_spec(dependency: Any) -> bool:
        # Only conda entries count. A nested "pip:" list is a dict here, and pip
        # installs it after the conda solve.
        return isinstance(dependency, str) and bool(
            _SETUPTOOLS_SPEC.match(dependency.strip())
        )
