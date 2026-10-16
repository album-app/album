import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from album.core import __version__ as album_version
from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import (
    DEFAULT_SOLUTION_ENV_CONTENT,
    DefaultValues,
)
from album.core.model.link import Link
from album.core.utils.operations.file_operations import (
    construct_cache_link_target,
    create_path_recursively,
    remove_link,
)
from album.core.utils.operations.resolve_operations import (
    dict_to_coordinates,
    get_parent,
)
from album.core.utils.operations.solution_operations import (
    get_replicability_reasons,
    get_solution_folder,
    set_environment_paths,
)
from album.environments.api.environment_api import IEnvironmentAPI
from album.environments.api.model.environment import IEnvironment
from album.environments.initialization import init_environment_handler
from album.environments.model.environment import Environment
from album.environments.utils.file_operations import (
    get_dict_from_yml,
    write_dict_to_yml,
)
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
        self,
        collection_solution: ICollectionSolution,
        allow_recursive: bool = False,
        no_conda_lock: bool = False,
    ) -> IEnvironment:
        environment = self._create_environment_for_solution(
            collection_solution, allow_recursive, no_conda_lock
        )
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def _create_environment_for_solution(
        self,
        collection_solution: ICollectionSolution,
        allow_recursive: bool = False,
        no_conda_lock: bool = False,
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
        self._warn_without_lock_file(
            collection_solution.coordinates(), solution_package_path, no_conda_lock
        )
        environment = self.create_environment(
            cache,
            dependencies,
            env_name,
            album_api_version,
            solution_package_path,
            allow_recursive,
            solution_folder=get_solution_folder(collection_solution),
            no_conda_lock=no_conda_lock,
        )
        set_environment_paths(collection_solution.loaded_solution(), environment)
        return environment

    def check_lock_file(
        self,
        coordinates: ICoordinates,
        solution_folder: Optional[Path],
        no_conda_lock: bool = False,
    ) -> None:
        lock_file = (
            solution_folder.joinpath(
                DefaultValues.solution_conda_lock_default_name.value
            )
            if solution_folder is not None
            else None
        )
        if no_conda_lock or lock_file is None or not lock_file.is_file():
            return
        try:
            self._environment_handler.get_conda_lock_manager().conda_lock_executable()
        except RuntimeError as e:
            raise RuntimeError(
                f'"{coordinates}" is installed from its lock file, but conda-lock, which '
                "installs it, is not found. Set ENVIRONMENT_CONDA_LOCK_PATH to the "
                "conda-lock executable, or install it with --no-conda-lock to solve its "
                "environment instead."
            ) from e

    def _warn_without_lock_file(
        self,
        coordinates: ICoordinates,
        solution_package_path: Path,
        no_conda_lock: bool = False,
    ) -> None:
        """Warn when the environment of a solution is solved now, not taken from a lock file.

        A lock file is solved again only with no_conda_lock: without it, installing fails if
        conda-lock, which installs it, is not found.
        """
        lock_file = solution_package_path.joinpath(
            DefaultValues.solution_conda_lock_default_name.value
        )
        if lock_file.is_file() and no_conda_lock:
            module_logger().warning(
                f'Not technically replicable, "{coordinates}": it is installed without its '
                "lock file (--no-conda-lock), its environment is solved now."
            )
        elif lock_file.is_file():
            self.check_lock_file(coordinates, solution_package_path)
        elif not get_replicability_reasons(solution_package_path):
            # a solution deployed without a lock file says so in the reasons shown already
            module_logger().warning(
                f'Not technically replicable, "{coordinates}": it has no lock file, its '
                "environment is solved now."
            )

    def create_environment(
        self,
        cache: Path,
        dependencies: Dict[str, Any],
        env_name: str,
        album_api_version: str,
        solution_package_path: Path,
        allow_recursive: bool = False,
        solution_folder: Optional[Path] = None,
        no_conda_lock: bool = False,
    ) -> IEnvironment:
        """Create the environment of a solution.

        A deployed solution is installed from what album deploy wrote next to it: its lock
        file, or else the environment it locked, not from the environment file it names. A
        relative path of the environment file starts at solution_folder, the folder the
        solution is installed from; None for a solution installed from a single file. With
        no_conda_lock, the environment is solved even if the solution has a lock file.
        """
        environment_snapshot = solution_package_path.joinpath(
            DefaultValues.solution_environment_default_name.value
        )
        env_file = self._prepare_env_file(
            dependencies,
            cache,
            env_name,
            album_api_version,
            allow_recursive,
            solution_folder=solution_folder,
            environment_snapshot=(
                environment_snapshot if environment_snapshot.is_file() else None
            ),
        )
        env_path = self.get_environment_path(env_name, create=True)
        environment = Environment(env_file, env_name, env_path)
        solution_lock_file = solution_package_path.joinpath(
            DefaultValues.solution_conda_lock_default_name.value
        )
        if no_conda_lock:
            # solved as create_environment_prefer_lock_file does without a lock file
            self._environment_handler.get_package_manager().install(environment)
            return environment
        try:
            self._environment_handler.create_environment_prefer_lock_file(
                environment, str(solution_lock_file.absolute())
            )
        except RuntimeError as e:
            if not solution_lock_file.is_file():
                raise
            # the output of conda-lock is in the log, the error names only the command
            raise RuntimeError(
                f"Installing the environment from the lock file failed: {e}. If the lock "
                "file does not install on this system, install the solution with "
                "--no-conda-lock to solve its environment instead."
            ) from e

        return environment

    @staticmethod
    def _is_running_album_version(version_str: str) -> bool:
        try:
            return Version(version_str) == Version(album_version)
        except InvalidVersion:
            return version_str == album_version

    @staticmethod
    def _conda_album_dependency(dependency: str) -> Optional[bool]:
        """Check a conda dependency (a match spec) for album.

        Returns None if the dependency is not album, True if it is album without a
        version or with exactly the running version, and False for any other version
        spec, e.g. another version or a range.
        """
        # e.g. "album", "album=0.1.0", "album 0.1.0 py_0", "conda-forge::album>=0.1"
        spec = dependency.strip().split("::")[-1]
        match = re.match(r"([A-Za-z0-9_.\-]+)\s*(.*)$", spec)
        if not match or match.group(1).lower() != "album":
            return None
        version_spec = match.group(2).strip()
        bracket = re.match(
            r"^\[\s*version\s*=\s*[\"']?([^\"'\],]*)[\"']?\s*\]$", version_spec
        )
        if bracket:  # album[version='0.1.0']
            version_spec = bracket.group(1).strip()
        if not version_spec:
            return True
        # one exact version, as "=0.1.0", "==0.1.0" or "0.1.0", optionally followed by a build
        exact = re.match(
            r"^(?:==?)?\s*([0-9][0-9A-Za-z._+!\-]*)(?:[=\s].*)?$", version_spec
        )
        if not exact:
            return False
        return EnvironmentManager._is_running_album_version(exact.group(1))

    @staticmethod
    def _pip_album_dependency(dependency: str) -> Optional[bool]:
        """Check a pip dependency (a requirement) for album, see _conda_album_dependency."""
        try:
            requirement = Requirement(dependency)
        except InvalidRequirement:  # e.g. an option like "--index-url ..."
            return None
        if canonicalize_name(requirement.name) != "album":
            return None
        if requirement.url:  # album @ git+https://...
            return False
        specifiers = list(requirement.specifier)
        if not specifiers:
            return True
        if (
            len(specifiers) == 1
            and specifiers[0].operator in ("==", "===")
            and "*" not in specifiers[0].version
        ):
            return EnvironmentManager._is_running_album_version(specifiers[0].version)
        return False

    def _check_album_in_album(
        self, yml_dict: Dict[str, Any], allow_recursive: bool = False
    ) -> None:
        # every album dependency, with whether it is the running version (or unversioned)
        album_dependencies: List[Tuple[str, bool]] = []
        for dep in yml_dict.get("dependencies") or []:
            if isinstance(dep, dict):
                for pip_dep in dep.get("pip") or []:
                    running = self._pip_album_dependency(str(pip_dep))
                    if running is not None:
                        album_dependencies.append(("pip: %s" % pip_dep, running))
            elif isinstance(dep, str):
                running = self._conda_album_dependency(dep)
                if running is not None:
                    album_dependencies.append((dep, running))

        if not album_dependencies:
            return

        other_versions = [dep for dep, running in album_dependencies if not running]
        if not other_versions:
            module_logger().warning(
                "Album is planned to be installed in the solution environment. "
                "This might cause issues when sharing the same database! "
                "Only proceed if you know what you are doing!"
            )
            return

        str_ = (
            "Album is planned to be installed in the solution environment with a different version"
            ' ("%s", running album %s).' % ('", "'.join(other_versions), album_version)
            + " They might be incompatible! It is recommended to update the parent solution!"
            " If you know what you are doing, set allow_recursive during installation!"
        )
        if not allow_recursive:
            module_logger().error(str_)
            raise ValueError(str_)
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

        # solution runs in the environment of the solution at the top of its parent
        # chain: a parent can have a parent itself, and only the top one has an
        # environment (InstallManager._install_active_solution creates no other)
        else:
            root = get_parent(db_entry)
            coordinates = dict_to_coordinates(root.setup())
            catalog = self._album.catalogs().get_by_id(root.internal()["catalog_id"])
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
        solution_folder: Optional[Path] = None,
        environment_snapshot: Optional[Path] = None,
    ) -> Path:
        yaml_path = cache_path.joinpath("{n}{s}".format(n=env_name, s=".yml"))
        create_path_recursively(yaml_path.parent)
        if environment_snapshot is not None:
            # the environment album deploy locked, album-solution-api added already
            yaml_dict = get_dict_from_yml(environment_snapshot)
            yaml_dict["name"] = env_name
            self._check_album_in_album(yaml_dict, allow_recursive)
            write_dict_to_yml(yaml_path, yaml_dict)
            return yaml_path

        yaml_dict = None
        if dependencies_dict:
            if "environment_file" in dependencies_dict:
                env_file = dependencies_dict["environment_file"]

                # a relative path starts at the folder solution.py is installed from
                self._album.resource_manager().handle_env_file_dependency(
                    env_file, yaml_path, solution_folder
                )

                yaml_dict = get_dict_from_yml(yaml_path)
                yaml_dict["name"] = env_name

        if not album_api_version:
            album_api_version = DefaultValues.runner_api_package_version.value

        # track whether the environment comes from the solution or from defaults
        has_user_environment = yaml_dict is not None

        if not yaml_dict:
            yaml_dict = deepcopy(DEFAULT_SOLUTION_ENV_CONTENT)
            # Keep the Anaconda "defaults" channels out, even when the user's conda
            # configuration (e.g. ~/.condarc) lists them. Not part of
            # DEFAULT_SOLUTION_ENV_CONTENT, which deploy also hands to conda-lock:
            # conda-lock overrides the channels anyway, and before 2.0 it took
            # "nodefaults" for a channel name.
            yaml_dict["channels"].append("nodefaults")

        # safety check to avoid album in album issues
        self._check_album_in_album(yaml_dict, allow_recursive)

        # package name
        runner_package_name = DefaultValues.runner_api_package_name.value

        # if specified, install the outdated runner
        if self._album.migration_manager().is_migration_needed_solution_api(
            album_api_version
        ):
            config = self._album.migration_manager().get_outdated_environment_config()
            runner_package_name = config["runner_package_name"]
            album_api_version = config["runner_version"]
            # Only pin Python and setuptools when using the default environment.
            # User-provided environments are left untouched — the user owns
            # their dependency specification and we should not risk conflicts
            # with their conda/pip dependency layout.
            if not has_user_environment:
                EnvironmentManager._apply_outdated_environment_pins(
                    yaml_dict,
                    config["python_version"],
                    config["extra_pins"],
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
        # Only inspect the configured string itself. Probing the filesystem
        # (e.g. Path(...).is_dir()) depends on the current working directory and
        # rejects a valid package name whenever a folder of the same name exists
        # there, such as a checkout of album-solution-api.
        framework_name = DefaultValues.runner_api_package_name.value
        if (
            "/" in framework_name
            or os.sep in framework_name
            or framework_name.endswith(".zip")
            or framework_name.startswith("https")
        ):
            raise ValueError(
                "Framework is not properly defined. No zip, https or folder allowed."
            )

        return EnvironmentManager._append_framework_via_conda_to_yml(
            content, album_api_version, runner_package_name
        )

    @staticmethod
    def _apply_outdated_environment_pins(
        yaml_dict: Dict[str, Any],
        python_version: str,
        extra_pins: List[str],
    ) -> None:
        """Replace the Python version and add extra dependency pins for the default environment of outdated solutions.

        Only called when the solution does NOT provide its own environment file, so we are safe to modify the
        auto-generated dependency list.
        """
        if "dependencies" not in yaml_dict or not yaml_dict["dependencies"]:
            yaml_dict["dependencies"] = []
        yaml_dict["dependencies"] = [
            (
                "python=%s" % python_version
                if isinstance(dep, str) and dep.startswith("python=")
                else dep
            )
            for dep in yaml_dict["dependencies"]
        ]
        yaml_dict["dependencies"].extend(extra_pins)

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
