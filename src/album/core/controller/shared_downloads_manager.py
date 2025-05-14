import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

import pooch
import validators
from album.environments.utils.file_operations import get_dict_from_yml
from album.environments.utils.url_operations import download_resource
from album.runner.album_logging import get_active_logger

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.shared_downloads_manager import IDownloadManager
from album.core.api.model.collection_solution import ICollectionSolution


class DownloadManager(IDownloadManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def download_resources_from_yaml(
        self, collection_solution: ICollectionSolution
    ) -> bool:
        resources_dict, resources_json_path = self._resources_yaml_to_dict(
            collection_solution
        )
        if resources_dict:
            self._retrieve_resources_from_dict(resources_dict)
            self._set_file_paths_in_json(resources_dict, resources_json_path)
        return True

    def _resources_yaml_to_dict(
        self, collection_solution: ICollectionSolution
    ) -> Tuple[Dict[str, Any], Path]:
        """_summary_

        Args:
            collection_solution (ICollectionSolution): current solution to get the resources for

        Returns:
            dict: Resources dictionary, including their paths. Paths do NOT contain the resource name!
            Path: Path to the resource yaml file
        """

        # Get solution names and storage paths needed
        coords = collection_solution.coordinates()
        sol_name = "_".join([coords.group(), coords.name(), coords.version()])

        catalog_name = collection_solution.catalog().name()

        cache_path = (
            collection_solution.loaded_solution().installation().internal_cache_path()
        )

        app_path = collection_solution.loaded_solution().installation().app_path()

        # Get the resource file from the solution dependencies
        dependencies = collection_solution.loaded_solution().setup().dependencies
        # TODO: change to json file and implement json handling in the same way as yaml
        # NOTE: json is native to python, yaml is not
        resource_json_path = self._prepare_resource_file(
            dependencies, cache_path, sol_name
        )

        # Get shared globally path
        shared_globally_path = self.album.configuration().shared_resources_path()

        if not resource_json_path:
            return None  # todo: wrong return type

        # Get the resources from the yaml file and set the paths
        resources_dict = get_dict_from_yml(resource_json_path)
        self._set_paths_in_dict(
            resources_dict,
            app_path,
            catalog_name,
            shared_globally_path,
        )

        return resources_dict, resource_json_path

    @staticmethod
    def _prepare_resource_file(
        dependencies_dict: Dict[str, Any], cache_path: Path, env_name: str
    ) -> Path:
        """Checks if a resource file is provided. Returns a path to a valid json file.

        Args:
            dependencies_dict (_type_): _description_
            chache_path (_type_): _description_

        Returns:
            _type_: _description_
        """
        if dependencies_dict:
            if "resource_file" in dependencies_dict:
                resource_file = dependencies_dict["resource_file"]

                json_path = cache_path.joinpath(
                    "{}{}".format(env_name, "_resource_file.json")
                )

                # in case the file already exists, there is no need to create it again
                if json_path.exists() and json_path.is_file():
                    return json_path  # TODO: think about allowing updating this file
                    # TODO: remind JPA that icache folder was never a cache folder but a storage folder,
                    # hence i am using it to store the resource yaml, write the paths in it, and read it on the API side

                Path(json_path.parent).mkdir(parents=True, exist_ok=True)

                if isinstance(resource_file, str):
                    # case valid url
                    if validators.url(resource_file):
                        yaml_path = download_resource(resource_file, json_path)
                        resources_dict = get_dict_from_yml(yaml_path)
                        # save resources_dict as json file in the same location
                        with open(str(json_path).replace(".yml", ".json"), "w+") as f:
                            json.dump(resources_dict, f, indent=4)
                    # case file content
                    elif "resources:" in resource_file and "\n" in resource_file:
                        with open(json_path, "w+") as f:
                            f.write(resource_file)
                        resources_dict = get_dict_from_yml(json_path)
                        # save resources_dict as json file in the same location
                        with open(str(json_path), "w+") as f:
                            json.dump(resources_dict, f, indent=4)
                    # case Path
                    elif (
                        Path(resource_file).is_file()
                        and Path(resource_file).stat().st_size > 0
                    ):
                        resources_dict = get_dict_from_yml(resource_file)
                        # save resources_dict as json file in the same location
                        with open(str(json_path), "w+") as f:
                            json.dump(resources_dict, f, indent=4)
                    else:
                        raise TypeError(
                            "resource_file must either contain the content of the resource file, "
                            "contain the url to a valid file or point to a file on the disk!"
                        )
                # case dict
                elif isinstance(resource_file, dict):
                    with open(str(json_path), "w+") as f:
                        json.dump(resource_file, f, indent=4)

                else:
                    raise RuntimeError(
                        "Resource file specified, but format is unknown!"
                        " Don't know where to run solution!"
                    )

                return json_path
            return None  # todo: wrong return type
        return None  # todo: wrong return type

    def _retrieve_resources_from_dict(self, resources_dict: Dict[str, Any]) -> None:
        """
        Downloads the files specified in the dictionary.

        Args:
            resources_dict:
                Resources dictionary with resolved paths in regard to scope.

        Returns:
            None, if it worked.
        """

        for _, resource_value in resources_dict["resources"].items():
            if "os" in resource_value and not resource_value["os"] == sys.platform:
                continue

            try:
                fpath = pooch.retrieve(
                    url=resource_value["url"],
                    known_hash=resource_value["hash"],
                    fname=resource_value["name"],
                    path=str(resource_value["path"]),
                    progressbar=True,
                )
            except Exception as e:
                get_active_logger().error(f"Failed to download resource: {e}")
                fpath = None

            get_active_logger().info(f"Downloaded a resource to {fpath}")
            if resource_value["hash"] is None:
                get_active_logger().info(
                    f"Resource {resource_value['name']} has no hash provided in the resource file. \n"
                    "Therefore, if the requested file already exists in the target directory, it will be used without checking if the hashes match. \n"
                    "You can copy the following md5 hash of the just obtained file to the resource file to enforce reproducibility before deployment: \n"
                    f"{pooch.file_hash(fpath, alg='md5')}"
                )
        return None

    def _set_paths_in_dict(
        self,
        resources_dict: Dict[str, Any],
        app_path: Path,
        catalog_name: str,
        shared_globally_path: Path,
    ) -> Dict[str, Any]:
        """
        Sets the paths of the downloaded resources in the resources dictionary.
        """
        for _, resource_value in resources_dict["resources"].items():
            # Default scope: fully shared / global scope
            if "scope" not in resource_value:
                resource_value["scope"] = "global"

            if resource_value["scope"] == "global":
                resource_value["path"] = shared_globally_path
            if resource_value["scope"] == "catalog":
                resource_value["path"] = shared_globally_path / catalog_name
            if resource_value["scope"] == "solution":
                resource_value["path"] = app_path

        return resources_dict

    @staticmethod
    def _set_file_paths_in_json(
        resources_dict: Dict[str, Any], json_path: Path
    ) -> Dict[str, Any]:
        """
        Sets the full file paths into the dict and overwrites the json file.
        """
        for _, resource_value in resources_dict["resources"].items():
            resource_value["path"] = str(
                Path(resource_value["path"]) / resource_value["name"]
            )

        # write dict to json
        with open(json_path, "w") as f:
            json.dump(resources_dict, f, indent=4)

        return resources_dict
