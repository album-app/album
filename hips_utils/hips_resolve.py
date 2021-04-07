from hips_utils.hips_configuration import HipsConfiguration
from hips_utils import hips_logging


module_logger = hips_logging.get_active_logger


def resolve_hips(hips_dependency):
    """Resolves the hips and returns the path to the solution.py file on the current system."""
    # load the configured Catalogs
    configuration = HipsConfiguration()

    # resolve in order of catalogs specified in config file
    for catalog in configuration.catalogs:

        # update if necessary and possible
        if not catalog.is_local:
            catalog.update_catalog()

        # resolve via doi
        if "doi" in hips_dependency.keys():
            path_to_solution = catalog.resolve_doi(hips_dependency["doi"])
        else:  # resolve via group, name, version
            group = hips_dependency["group"]
            name = hips_dependency["name"]
            version = hips_dependency["version"]

            path_to_solution = catalog.resolve(group, name, version)

        return {
            "path": path_to_solution,
            "catalog": catalog.id
        }

    raise RuntimeError("Could not resolve hip dependency! %s" % hips_dependency)


def get_search_index():
    """Allow searching through all depth 3 leaves (solution entries) of all configured catalogs."""
    hips_config = HipsConfiguration()
    catalog_indices_dict = {}
    for catalog in hips_config.catalogs:
        module_logger().debug("Load catalog leaves for catalog: %s..." % catalog.id)
        catalog_indices_dict[catalog.id] = catalog.catalog_index.get_leaves_dict_list()

    return catalog_indices_dict


def get_installed_solutions():
    hips_config = HipsConfiguration()
    installed_solutions_dict = {}
    for catalog in hips_config.catalogs:
        module_logger().debug("Get installed solutions from catalog: %s..." % catalog.id)
        installed_solutions_dict[catalog.id] = catalog.list_installed()

    return installed_solutions_dict
