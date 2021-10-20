from io import StringIO
from pathlib import Path

import validators

from album.core.utils.operations.file_operations import create_path_recursively, copy, write_dict_to_yml, \
    get_dict_from_yml
from album.core.utils.operations.url_operations import download_resource
from album.runner import logging

module_logger = logging.get_active_logger


class Environment:
    """Class managing an environment a solution lives in.

    Each solution lives in its own environment having different dependencies. These can be libraries, programs, etc.
    Each environment has its own environment path and is identified by such. Each album environment has to have
    the album-runner installed for the album framework to be able to run the solution in its environment.
    An environment can be set up by environment file or only by name.

    """

    def __init__(self, dependencies_dict, environment_name, cache_path):
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
        self.name = environment_name
        self.cache_path = Path(cache_path)
        self.yaml_file = self.prepare_env_file(dependencies_dict)
        self.path = None

    def prepare_env_file(self, dependencies_dict):
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
            if 'environment_file' in dependencies_dict:
                env_file = dependencies_dict['environment_file']

                yaml_path = self.cache_path.joinpath(
                    "%s%s" % (self.name, ".yml"))
                create_path_recursively(yaml_path.parent)

                if isinstance(env_file, str):
                    # case valid url
                    if validators.url(env_file):
                        yaml_path = download_resource(env_file, yaml_path)
                    # case Path
                    elif Path(env_file).is_file() and Path(env_file).stat().st_size > 0:
                        yaml_path = copy(env_file, yaml_path)
                    else:
                        raise TypeError("Yaml file must either be a url to a valid file"
                                        " or point to a file on the disk!")
                # case String stream
                elif isinstance(env_file, StringIO):
                    with open(yaml_path, "w+") as f:
                        env_file.seek(0)  # make sure we start from the beginning
                        f.writelines(env_file.readlines())
                    yaml_path = yaml_path
                else:
                    raise RuntimeError('Environment file specified, but format is unknown!'
                                       ' Don\'t know where to run solution!')

                yaml_dict = get_dict_from_yml(yaml_path)
                yaml_dict["name"] = self.name
                write_dict_to_yml(yaml_path, yaml_dict)

                return yaml_path
            return None
        return None
