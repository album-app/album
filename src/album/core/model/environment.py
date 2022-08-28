from io import StringIO
from pathlib import Path

import validators

from album.core.api.model.environment import IEnvironment
from album.core.utils.operations.file_operations import (
    create_path_recursively,
    copy,
    write_dict_to_yml,
    get_dict_from_yml,
)
from album.core.utils.operations.url_operations import download_resource
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class Environment(IEnvironment):
    def __init__(self, dependencies_dict, environment_name, cache_path: Path):
        """Init routine

        Args:
            dependencies_dict:
                Can be None or hold the entries a) "environment_file" b) "environment_name"
            environment_name:
                name prefix for all files to cache.
                Used when "name" is not available during yaml-file download for example.
            cache_path:
                cache path where to store downloads (yaml file, etc.)
        """
        self._name = environment_name
        self._cache_path = cache_path
        self._yaml_file = self._prepare_env_file(dependencies_dict)
        self._path = None

    def _prepare_env_file(self, dependencies_dict):
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

                yaml_path = self._cache_path.joinpath("%s%s" % (self._name, ".yml"))
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
                yaml_dict["name"] = self._name
                write_dict_to_yml(yaml_path, yaml_dict)

                return yaml_path
            return None
        return None

    def name(self):
        return self._name

    def cache_path(self):
        return self._cache_path

    def yaml_file(self):
        return self._yaml_file

    def path(self):
        return self._path

    def set_path(self, path):
        self._path = path
