from hips.core.model.catalog_configuration import HipsCatalogCollection
from hips_runner import logging

module_logger = logging.get_active_logger


class CatalogManager:
    """Class to add, remove and manage catalogs.

     Attributes:
         catalog_configuration:
            The configuration of the HIPS framework installation.

    """

    catalog_configuration = None

    def __init__(self):
        self.catalog_configuration = HipsCatalogCollection()

    def add(self, path):
        """ Adds a catalog to the configuration."""
        self.catalog_configuration.config_file_dict["catalogs"].append(path)
        self.catalog_configuration.save()

        module_logger().info('Added catalog %s!' % path)

    def remove(self, path):
        """Removes a catalog from a configuration"""
        self.catalog_configuration.config_file_dict["catalogs"].remove(path)
        self.catalog_configuration.save()

        module_logger().info('Removed catalog %s!' % path)
