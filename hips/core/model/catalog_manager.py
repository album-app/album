from hips.core.model import logging
from hips.core.model.configuration import HipsCatalogConfiguration

module_logger = logging.get_active_logger


class HipsCatalogManager:

    catalog_configuration = None

    def __init__(self):
        self.catalog_configuration = HipsCatalogConfiguration()

    def add(self, args):
        """Function corresponding to the `add-catalog` subcommand of `hips`."""
        self.catalog_configuration.config_file_dict["catalogs"].append(args.path)
        self.catalog_configuration.save()

        module_logger().info('Added catalog %s!' % args.path)

    def remove(self, args):
        """Function corresponding to the `remove-catalog` subcommand of `hips`."""
        self.catalog_configuration.config_file_dict["catalogs"].remove(args.path)
        self.catalog_configuration.save()

        module_logger().info('Removed catalog %s!' % args.path)
