from pathlib import Path

import validators

from hips.api import get_cache_path_catalog, get_configuration_file_path, _extract_catalog_name
from hips.hips_base import HipsDefaultValues
from hips_utils import hips_logging
from hips_utils.hips_catalog import Catalog
from hips_utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml, create_path_recursively

module_logger = hips_logging.get_active_logger


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

        module_logger().debug("Configuration looks like: %s" % config_file_dict)

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
            module_logger().debug("Try to initialize the following catalog: %s" % catalog)

            id = _extract_catalog_name(catalog)
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

