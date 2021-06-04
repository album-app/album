from hips.core.controller.catalog_manager import CatalogManager


hips_catalog_manager = CatalogManager()


def add_catalog(args):
    hips_catalog_manager.add(args.path)


def remove_catalog(args):
    hips_catalog_manager.remove(args.path)



