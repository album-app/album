from hips.core.concept.singleton import Singleton

from hips.core.model.catalog_collection import HipsCatalogCollection
from hips_runner import logging

module_logger = logging.get_active_logger


class CatalogManager(metaclass=Singleton):
    """Class to add, remove and manage catalogs.

    In a catalog, solutions of any kind are registered.
    Each installation instance of the hips framework can hold arbitrary many catalogs.
    With this class, the collection of catalogs can be managed.

     Attributes:
         catalog_collection:
            Holds all the catalogs of the HIPS framework installation.

    """
    # singletons
    catalog_collection = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = HipsCatalogCollection() if not catalog_collection else catalog_collection

    def add(self, path):
        """ Adds a catalog to the configuration."""
        self.catalog_collection.config_file_dict["catalogs"].append(path)
        self.catalog_collection.save()

        module_logger().info('Added catalog %s!' % path)

    def remove(self, path):
        """Removes a catalog from a configuration"""
        self.catalog_collection.config_file_dict["catalogs"].remove(path)
        self.catalog_collection.save()

        module_logger().info('Removed catalog %s!' % path)
