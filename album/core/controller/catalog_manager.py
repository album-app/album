from album.core.concept.singleton import Singleton

from album.core.model.catalog_collection import CatalogCollection
from album_runner import logging

module_logger = logging.get_active_logger


class CatalogManager(metaclass=Singleton):
    """Class to add, remove and manage catalogs.

    In a catalog, solutions of any kind are registered.
    Each installation instance of the album framework can hold arbitrary many catalogs.
    With this class, the collection of catalogs can be managed.

     Attributes:
         catalog_collection:
            Holds all the catalogs of the album framework installation.

    """
    # singletons
    catalog_collection = None

    def __init__(self):
        self.catalog_collection = CatalogCollection()

    def add(self, path):
        """ Adds a catalog to the configuration."""
        self.catalog_collection.config_file_dict["catalogs"].append(path)
        self.catalog_collection.save()
        self.catalog_collection.reload()

        module_logger().info('Added catalog %s!' % path)

    def remove(self, path):
        """Removes a catalog from a configuration"""
        self.catalog_collection.config_file_dict["catalogs"].remove(path)
        self.catalog_collection.save()
        self.catalog_collection.reload()

        module_logger().info('Removed catalog %s!' % path)
