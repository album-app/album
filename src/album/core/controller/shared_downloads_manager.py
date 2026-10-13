import hashlib
import importlib.util
import json
import logging
import pkgutil
import sys
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Iterator, Optional

import pooch
import validators
import yaml
from jsonschema import ValidationError, validate

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.shared_downloads_manager import IDownloadManager
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
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

    def download_resources(
        self, collection_solution: ICollectionSolution
    ) -> Optional[Path]:
        solution = collection_solution.loaded_solution()
        resources_dict = self._load_resources(solution)
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

    def check_resources(self, solution: ISolution) -> None:
        resources_dict = self._load_resources(solution)
        if resources_dict is None:
            return

        # a string that is neither a url nor the content of the file is a path, see ResourceManager
        resource_file = solution.setup().dependencies["resource_file"]
        if (
            isinstance(resource_file, str)
            and not validators.url(resource_file)
            and not ("resources:" in resource_file and "\n" in resource_file)
        ):
            module_logger().warning(
                'The resource_file of "%s" points to the file %s. The solution can only be '
                "installed where this path exists. Add the content of the file to the solution "
                "or use a url instead." % (solution.coordinates(), resource_file)
            )

        for key, resource in resources_dict["resources"].items():
            if resource["scope"] != SCOPE_SOLUTION and not resource["hash"]:
                module_logger().warning(
                    'Resource "%s" of "%s" is shared, but has no hash. Every solution sharing '
                    "it will use the content that was downloaded first, whatever the url "
                    'returns later. Pin the content with a "hash".'
                    % (key, solution.coordinates())
                )

    def _load_resources(self, solution: ISolution) -> Optional[Dict[str, Any]]:
        """Read and validate the resource file of a solution, filled up with the default values.

        Returns:
            The resources dictionary, or None if the solution declares no resource file.
        """
        dependencies = solution.setup().dependencies
        if not dependencies or "resource_file" not in dependencies:
            return None

        # bring every form of the resource file to a yml file first
        yml_path = (
            self.album.configuration()
            .tmp_path()
            .joinpath(self._get_resources_file_name(solution.coordinates(), ".yml"))
        )
        try:
            self.album.resource_manager().handle_resource_file_dependency(
                dependencies["resource_file"], yml_path
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

    @staticmethod
    def _retrieve_resources_from_dict(resources_dict: Dict[str, Any]) -> None:
        """Download every resource with a path. A resource already on the disk is not downloaded again.

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
                with DownloadManager._quiet_pooch():
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
