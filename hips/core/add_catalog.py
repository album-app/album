from hips.core.model import logging
from hips.core.model.catalog_manager import HipsCatalogManager

module_logger = logging.get_active_logger


def add_catalog(args):
    HipsCatalogManager().add(args)

