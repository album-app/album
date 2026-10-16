import hashlib
import importlib.util
import json
import logging
import pkgutil
import sys
import threading
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Iterator, List, Optional

import pooch
import yaml
from jsonschema import ValidationError, validate

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.shared_downloads_manager import IDownloadManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.core.model.replicability import ReplicabilityReason
from album.core.utils.file_lock import FileLock
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.solution_operations import get_solution_folder
from album.runner.album_logging import get_active_logger
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

module_logger = get_active_logger

SCOPE_GLOBAL = "global"
SCOPE_CATALOG = "catalog"
SCOPE_SOLUTION = "solution"


def _is_warning_or_worse(record: logging.LogRecord) -> bool:
    return record.levelno >= logging.WARNING


class DownloadManager(IDownloadManager):
    def __init__(self, album: IAlbumController):
        self.album = album
        self._schema: Optional[Dict[str, Any]] = None
        # one lock per content folder of shared resources, see _get_resource_lock
        self._locks: Dict[Path, FileLock] = {}
        self._locks_creation = threading.Lock()

    def download_resources(
        self, collection_solution: ICollectionSolution
    ) -> Optional[Path]:
        solution = collection_solution.loaded_solution()
        # a deployed solution is installed from the resource list album deploy wrote next
        # to it, not from the resource file it names
        package_path = solution.installation().package_path()
        resource_snapshot = (
            Path(package_path).joinpath(
                DefaultValues.solution_resources_default_name.value
            )
            if package_path
            else None
        )
        resources_dict = self._load_resources(
            solution,
            get_solution_folder(collection_solution),
            (
                resource_snapshot
                if resource_snapshot is not None and resource_snapshot.is_file()
                else None
            ),
        )
        if resources_dict is None:
            return None

        self._set_paths_in_dict(
            resources_dict,
            solution.installation().installation_path(),
            collection_solution.catalog().name(),
            self.album.configuration().shared_resources_path(),
        )
        self._retrieve_resources_from_dict(resources_dict)

        # the json file is only written when every resource is available
        return self._write_resources_json(resources_dict, solution)

    def check_resources(
        self, solution: ISolution, solution_folder: Optional[Path] = None
    ) -> List[ReplicabilityReason]:
        resources_dict = self._load_resources(solution, solution_folder)
        if resources_dict is None:
            return []

        reasons = []
        for key, resource in resources_dict["resources"].items():
            from_doi = resource["url"].startswith("doi:")
            if resource["hash"]:
                if not from_doi:
                    module_logger().warning(
                        'Resource "%s" of "%s" is downloaded from %s, which can become '
                        "unavailable. A DOI, e.g. on Zenodo, keeps it available."
                        % (key, solution.coordinates(), resource["url"])
                    )
            elif from_doi:
                reasons.append(
                    ReplicabilityReason(
                        'resource "%s" has no hash, its content is not verified' % key
                    )
                )
            else:
                reasons.append(
                    ReplicabilityReason(
                        'resource "%s" is downloaded from %s without a hash, its content '
                        "can change" % (key, resource["url"]),
                        needs_flag=True,
                    )
                )
        return reasons

    def _load_resources(
        self,
        solution: ISolution,
        solution_folder: Optional[Path] = None,
        resource_snapshot: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        """Read and validate the resource file of a solution, filled up with the default values.

        A relative path of the resource file starts at solution_folder, the folder of the
        solution. resource_snapshot, the resource list album deploy wrote, is read instead.

        Returns:
            The resources dictionary, or None if the solution declares no resource file.
        """
        dependencies = solution.setup().dependencies
        if not dependencies or "resource_file" not in dependencies:
            return None
        resource_file = (
            str(resource_snapshot)
            if resource_snapshot is not None
            else dependencies["resource_file"]
        )

        # bring every form of the resource file to a yml file first
        yml_path = (
            self.album.configuration()
            .tmp_path()
            .joinpath(self._get_resources_file_name(solution.coordinates(), ".yml"))
        )
        try:
            self.album.resource_manager().handle_resource_file_dependency(
                resource_file, yml_path, solution_folder
            )
            with open(yml_path, encoding="utf-8") as yml_file:
                resources_dict = yaml.safe_load(yml_file)
        except yaml.YAMLError as e:
            raise ValueError(
                'The resource_file of "%s" is not valid YAML: %s'
                % (solution.coordinates(), e)
            ) from e
        finally:
            force_remove(yml_path)

        self._validate_resources(resources_dict, solution.coordinates())
        self._set_default_values(resources_dict)
        return resources_dict

    def _validate_resources(
        self, resources_dict: Any, coordinates: ICoordinates
    ) -> None:
        try:
            validate(resources_dict, self._get_schema())
        except ValidationError as e:
            location = "/".join(str(p) for p in e.absolute_path)
            raise ValueError(
                'The resource_file of "%s" is invalid%s: %s'
                % (coordinates, " at %s" % location if location else "", e.message)
            ) from e

        for key, resource in resources_dict["resources"].items():
            if not self._is_plain_file_name(resource["name"]):
                raise ValueError(
                    'The resource_file of "%s" is invalid: the name "%s" of resource "%s" '
                    "must be a plain file name, without any folder."
                    % (coordinates, resource["name"], key)
                )

    def _get_schema(self) -> Dict[str, Any]:
        if self._schema is None:
            data = pkgutil.get_data("album.core.schema", "resource_file_schema.json")
            if data is None:
                raise RuntimeError("The schema of the resource file is missing!")
            self._schema = json.loads(data)
        return self._schema

    @staticmethod
    def _is_plain_file_name(name: str) -> bool:
        """Tell whether a resource name can only point into the folder it is stored in."""
        return (
            name not in (".", "..")
            and PurePosixPath(name).name == name
            and PureWindowsPath(name).name == name
        )

    @staticmethod
    def _set_default_values(resources_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Add the optional keys of every resource. Resources without "os" are for every platform."""
        for resource in resources_dict["resources"].values():
            if resource.get("hash") is None:
                resource["hash"] = None
            if resource.get("os") is None:
                resource["os"] = None
            if resource.get("scope") is None:
                resource["scope"] = SCOPE_GLOBAL
        return resources_dict

    @staticmethod
    def _set_paths_in_dict(
        resources_dict: Dict[str, Any],
        installation_path: Path,
        catalog_name: str,
        shared_resources_path: Path,
    ) -> Dict[str, Any]:
        """Set the full path of every resource meant for the current platform, None for the others.

        A resource is stored in a folder named after its content, so resources only share
        a file when they ask for the same content::

            global:   <shared_resources_path>/global/<content folder>/<name>
            catalog:  <shared_resources_path>/catalog/<catalog name>/<content folder>/<name>
            solution: <installation_path>/resources/<content folder>/<name>
        """
        for resource in resources_dict["resources"].values():
            if resource["os"] not in (None, sys.platform):
                resource["path"] = None
                continue

            # album-solution-api selects the resources of the current platform by "os"
            resource["os"] = sys.platform

            if resource["scope"] == SCOPE_GLOBAL:
                scope_path = shared_resources_path.joinpath(SCOPE_GLOBAL)
            elif resource["scope"] == SCOPE_CATALOG:
                scope_path = shared_resources_path.joinpath(SCOPE_CATALOG, catalog_name)
            else:
                scope_path = installation_path.joinpath(
                    DefaultValues.solution_resources_prefix.value
                )

            resource["path"] = str(
                scope_path.joinpath(
                    DownloadManager._get_content_folder_name(resource),
                    resource["name"],
                )
            )
        return resources_dict

    @staticmethod
    def _get_content_folder_name(resource: Dict[str, Any]) -> str:
        """Name the folder of a resource after its hash, or after its url when it has no hash."""
        if resource["hash"]:
            algorithm, _, digest = resource["hash"].rpartition(":")
            # pooch takes a hash without an algorithm as sha256
            content = f"{(algorithm or 'sha256').lower()}:{digest.lower()}"
        else:
            content = resource["url"]
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _retrieve_resources_from_dict(self, resources_dict: Dict[str, Any]) -> None:
        """Download every resource with a path. A resource already on the disk is not downloaded again.

        A shared resource is retrieved holding the lock of its content folder, so solutions
        that are installed at the same time and share it download it once.

        Raises:
            RuntimeError: if a resource cannot be downloaded or does not match its hash.
        """
        for key, resource in resources_dict["resources"].items():
            if resource["path"] is None:
                continue

            path = Path(resource["path"])
            module_logger().info(
                f'Retrieving resource "{key}" from {resource["url"]}...'
            )
            try:
                with self._get_resource_lock(resource), DownloadManager._quiet_pooch():
                    pooch.retrieve(
                        url=resource["url"],
                        known_hash=resource["hash"],
                        fname=path.name,
                        path=str(path.parent),
                        progressbar=DownloadManager._show_progressbar(),
                    )
            except Exception as e:
                raise RuntimeError(
                    'Could not retrieve resource "%s" from %s: %s'
                    % (key, resource["url"], e)
                ) from e

            module_logger().info(f'Resource "{key}" is available at {path}.')
            if resource["hash"] is None:
                module_logger().info(
                    'Resource "%s" has no hash, its content is not verified. To pin the content, '
                    'add hash: "sha256:%s" to the resource.'
                    % (key, pooch.file_hash(str(path)))
                )

    def _get_resource_lock(self, resource: Dict[str, Any]) -> AbstractContextManager:
        """Return the lock of the content folder of a resource.

        A resource with scope "solution" belongs to one installation, and the lock of its
        solution is held while the solution is installed: it needs no lock of its own.
        """
        if resource["scope"] == SCOPE_SOLUTION:
            return nullcontext()

        # named after the content folder: the same content in two catalogs shares a lock
        lock_file = (
            self.album.configuration()
            .base_cache_path()
            .joinpath(
                DefaultValues.lock_folder_prefix.value,
                DefaultValues.resource_lock_folder_prefix.value,
                resource["scope"],
                "%s.lock" % Path(resource["path"]).parent.name,
            )
        )
        # one lock per file, so the threads of this process wait for each other as well
        with self._locks_creation:
            if lock_file not in self._locks:
                self._locks[lock_file] = FileLock(
                    lock_file,
                    timeout=DefaultValues.install_lock_timeout_in_seconds.value,
                    description='downloading the shared resource "%s"'
                    % resource["name"],
                )
            return self._locks[lock_file]

    @staticmethod
    @contextmanager
    def _quiet_pooch() -> Iterator[None]:
        """Keep the info messages of pooch out of the output, album reports the downloads itself."""
        # a filter, as the level of the pooch logger is cached: it is not registered with logging
        logger = pooch.get_logger()
        logger.addFilter(_is_warning_or_worse)
        try:
            yield
        finally:
            logger.removeFilter(_is_warning_or_worse)

    @staticmethod
    def _show_progressbar() -> bool:
        # pooch needs tqdm for a progress bar, which album does not depend on
        return (
            importlib.util.find_spec("tqdm") is not None
            and getattr(sys.stderr, "isatty", lambda: False)()
        )

    def _write_resources_json(
        self, resources_dict: Dict[str, Any], solution: ISolution
    ) -> Path:
        json_path = (
            solution.installation()
            .internal_cache_path()
            .joinpath(self._get_resources_file_name(solution.coordinates(), ".json"))
        )
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            # yaml can hold values json cannot, e.g. a date in an additional key of a resource
            json.dump(resources_dict, f, indent=4, default=str)
        return json_path

    @staticmethod
    def _get_resources_file_name(coordinates: ICoordinates, suffix: str) -> str:
        # album-solution-api (get_resources_dict) reads the json file under this name
        return "_".join(
            [
                coordinates.group(),
                coordinates.name(),
                coordinates.version(),
                "resource_file" + suffix,
            ]
        )
