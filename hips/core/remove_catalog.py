from hips.core.model.catalog_manager import HipsCatalogManager


def remove_catalog(args):
    HipsCatalogManager().remove(args)

