import os
import re
from pathlib import Path

import validators
from xdg import xdg_config_home, xdg_data_home

from hips.core.model.hips_base import HipsDefaultValues
from hips.core.model import logging
from hips.core.model.catalog import Catalog
from hips.core.model.resolve import module_logger
from hips.core.utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml, create_path_recursively

module_logger = logging.get_active_logger


def get_configuration_file_path():
    """Get the path to the HIPS runtime configuration file."""
    return xdg_config_home().joinpath(HipsDefaultValues.hips_config_file_name.value)


def get_base_cache_path():
    """Get path to local HIPS cache directory"""
    return xdg_data_home().joinpath("hips")


def get_cache_path_hips(active_hips):
    """Get the cache path of the active hips

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("solutions", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("solutions", "local", active_hips["group"], active_hips["name"], active_hips["version"])


def get_cache_path_app(active_hips):
    """Get the app cache path of the active hips

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of any apps belonging to a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("apps", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("apps", "local", active_hips["group"], active_hips["name"], active_hips["version"])


def get_cache_path_downloads(active_hips):
    """Get the cache path of anything a hips downloads.

    Args:
        active_hips: The HIPS object

    Returns: Path to local cache of any download files belonging to a HIPS

    """
    if hasattr(active_hips, "doi"):
        return get_base_cache_path().joinpath("downloads", "doi", active_hips["doi"])
    else:
        return get_base_cache_path().joinpath("downloads", "local", active_hips["group"], active_hips["name"], active_hips["version"])


def get_cache_path_catalog(catalog_id):
    """Get the cache path to the catalog with a certain ID.

    Args:
        catalog_id: The ID of the HIPS catalog

    Returns: Path to local cache of a catalog identified by the ID

    """
    return get_base_cache_path().joinpath("catalogs", catalog_id)


def extract_catalog_name(catalog_repo):
    """Extracts a basename from a repository URL.

    Args:
        catalog_repo:
            The repository URL or ssh string of the catalog.

    Returns:
        The basename of the repository

    """
    name, _ = os.path.splitext(os.path.basename(catalog_repo))
    return name


def create_default_hips_configuration():
    """Creates the default hips configuration dictionary which will be written in the hips configuration yaml file."""
    config_file_dict = {
        "catalogs": create_default_catalog_configuration(),
        # here more defaults can follow
    }

    return config_file_dict


def create_default_catalog_configuration():
    """Returns the default catalog configuration."""
    return [
        str(get_cache_path_catalog(HipsDefaultValues.local_catalog_name.value)),
        HipsDefaultValues.catalog.value,
    ]


class HipsConfiguration:
    """The Hips Configuration class. Also holds the catalogs specified in the configuration."""

    def __init__(self, config_file=None):
        if config_file:
            self.config_file_path = Path(config_file)
        else:
            self.config_file_path = get_configuration_file_path()
        self.config_file_dict = self._load_hips_configuration()
        self.catalogs = self._get_catalogs()
        self.local_catalog = self._get_local_catalog()

    @staticmethod
    def _create_default_configuration():
        """Creates the default configuration. Returns the corresponding dictionary"""
        module_logger().info("Creating default configuration...")
        config_file_dict = create_default_hips_configuration()
        return config_file_dict

    def get_default_deployment_catalog(self):
        """Returns first catalog which is not local. This is used as default deployment catalog."""
        for catalog in self.catalogs:
            if not catalog.is_local:
                return catalog
        return None

    def save(self, config_file_dict=None):
        """Saves the configuration dictionary to disk. Uses the file path specified in the HipsConfiguration object."""
        module_logger().info("Saving configuration file in %s..." % self.config_file_path)
        if not config_file_dict:
            config_file_dict = self.config_file_dict

        module_logger().debug("Configuration looks like: %s..." % config_file_dict)

        # make sure path to configuration file exists before creating configuration file
        create_path_recursively(self.config_file_path.parent)

        return write_dict_to_yml(self.config_file_path, config_file_dict)

    def _load_hips_configuration(self):
        """Loads a configuration.

         Either from disk (if the path specified in the HipsConfiguration object is a valid file)
         or from default values.

         """
        if self.config_file_path.is_file():
            module_logger().info("Load configuration from file %s..." % self.config_file_path)
            config_file_dict = get_dict_from_yml(self.config_file_path)
            if not config_file_dict:
                raise IOError("Empty configuration file!")
        else:
            config_file_dict = self._create_default_configuration()
            module_logger().info("Saving default configuration in file %s..." % self.config_file_path)
            self.save(config_file_dict)

        return config_file_dict

    def _get_catalogs(self):
        """Creates the catalog objects from the catalogs specified in the configuration."""
        try:
            cs = self.config_file_dict["catalogs"]
        except KeyError:
            raise RuntimeError("No catalogs configured!")

        catalogs = []

        for catalog in cs:
            module_logger().debug("Try to initialize the following catalog: %s..." % catalog)

            id = extract_catalog_name(catalog)
            src = None
            path = catalog

            # if entry is a valid url, we set the default path
            if validators.url(catalog):
                src = catalog
                path = get_cache_path_catalog(id)

            catalogs.append(Catalog(catalog_id=id, path=path, src=src))

        self.catalogs = catalogs

        return catalogs

    def _get_local_catalog(self):
        """Returns the first local catalog in the configuration (Reads yaml file from top)."""
        local_catalog = None
        for catalog in self.catalogs:
            if catalog.is_local:
                local_catalog = catalog
                break

        if local_catalog is None:
            raise RuntimeError("Misconfiguration of catalogs. There must be at least one local catalog!")

        self.local_catalog = local_catalog

        return local_catalog

    def get_search_index(self):
        """Allow searching through all depth 3 leaves (solution entries) of all configured catalogs."""
        catalog_indices_dict = {}
        for catalog in self.catalogs:
            module_logger().debug("Load catalog leaves for catalog: %s..." % catalog.id)
            catalog_indices_dict[catalog.id] = catalog.catalog_index.get_leaves_dict_list()

        return catalog_indices_dict

    def resolve(self, hips_attr):
        # resolve in order of catalogs specified in config file
        for catalog in self.catalogs:

            # update if necessary and possible
            if not catalog.is_local:
                catalog.refresh_index()

            # resolve via doi
            if "doi" in hips_attr.keys():
                path_to_solution = catalog.resolve_doi(hips_attr["doi"])
            else:  # resolve via group, name, version
                group = hips_attr["group"]
                name = hips_attr["name"]
                version = hips_attr["version"]

                path_to_solution = catalog.resolve(group, name, version)

            if not path_to_solution:
                continue

            return {
                "path": path_to_solution,
                "catalog": catalog
            }

        return None

    def resolve_hips_dependency(self, hips_dependency):
        """Resolves the hips and returns the path to the solution.py file on the current system."""

        r = self.resolve(hips_dependency)

        if not r:
            raise ValueError("Could not resolve hip dependency! %s" % hips_dependency)

    def resolve_from_str(self, str_input: str):
        """Resolves an command line input if in valid format."""
        p = Path(str_input)
        if p.is_file():
            return {
                "path": p,
                "catalog": None
            }
        else:
            p = self.get_doi_from_input(str_input)
            if not p:
                p = self.get_gnv_from_input(str_input)
                if not p:
                    raise ValueError("Invalid input format! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> or "
                                     "<group>:<name>:<version> or point to a valid file! Aborting...")
            module_logger().debug("Parsed %s from the input... " % p)
            return self.resolve_hips_dependency(p)

    def get_installed_solutions(self):
        """Returns all installed solutions by configured dictionary."""
        installed_solutions_dict = {}
        for catalog in self.catalogs:
            module_logger().debug("Get installed solutions from catalog: %s..." % catalog.id)
            installed_solutions_dict[catalog.id] = catalog.list_installed()

        return installed_solutions_dict

    @staticmethod
    def get_gnv_from_input(str_input: str):
        """Parses Group, Name, Version from input, separated by ":". """
        s = re.search('^([^:]+):([^:]+):([^:]+)$', str_input)

        if s:
            return {
                "group": s.group(1),
                "name": s.group(2),
                "version": s.group(3)
            }
        return None

    @staticmethod
    def get_doi_from_input(str_input: str):
        """Parses the DOI from string input."""
        s = re.search('^(^doi:)?([^:\/]*\/[^:\/]*)$', str_input)
        if s:
            return {
                "doi": s.group(2)
            }
        return None
