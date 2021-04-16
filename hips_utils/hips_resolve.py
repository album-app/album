import re
from pathlib import Path

from hips_utils.hips_configuration import HipsConfiguration
from hips_utils import hips_logging

module_logger = hips_logging.get_active_logger


def resolve_hips(hips_dependency):
    """Resolves the hips and returns the path to the solution.py file on the current system."""
    # load the configured Catalogs
    configuration = get_configuration()

    # resolve in order of catalogs specified in config file
    for catalog in configuration.catalogs:

        # update if necessary and possible
        if not catalog.is_local:
            catalog.refresh_index()

        # resolve via doi
        if "doi" in hips_dependency.keys():
            path_to_solution = catalog.resolve_doi(hips_dependency["doi"])
        else:  # resolve via group, name, version
            group = hips_dependency["group"]
            name = hips_dependency["name"]
            version = hips_dependency["version"]

            path_to_solution = catalog.resolve(group, name, version)

        if not path_to_solution:
            continue

        return {
            "path": path_to_solution,
            "catalog": catalog
        }

    raise ValueError("Could not resolve hip dependency! %s" % hips_dependency)


def resolve_from_str(str_input: str):

    p = Path(str_input)
    if p.is_file():
        return {
            "path": p,
            "catalog": None
        }
    else:
        p = get_doi_from_input(str_input)
        if not p:
            p = get_gnv_from_input(str_input)
            if not p:
                raise ValueError("Invalid input format! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> or "
                                 "<group>:<name>:<version> or point to a valid file! Aborting...")
        return resolve_hips(p)


def get_gnv_from_input(str_input: str):
    s = re.search('^([^:]+):([^:]+):([^:]+)$', str_input)

    if s:
        return {
            "group": s.group(1),
            "name": s.group(2),
            "version": s.group(3)
        }
    return None


def get_doi_from_input(str_input: str):
    s = re.search('^(^doi:)?([^:]*\/[^:]*)$', str_input)
    if s:
        return {
            "doi": s.group(2)
        }
    return None


def get_search_index():
    """Allow searching through all depth 3 leaves (solution entries) of all configured catalogs."""
    hips_config = get_configuration()
    catalog_indices_dict = {}
    for catalog in hips_config.catalogs:
        module_logger().debug("Load catalog leaves for catalog: %s..." % catalog.id)
        catalog_indices_dict[catalog.id] = catalog.catalog_index.get_leaves_dict_list()

    return catalog_indices_dict


def get_installed_solutions():
    hips_config = get_configuration()
    installed_solutions_dict = {}
    for catalog in hips_config.catalogs:
        module_logger().debug("Get installed solutions from catalog: %s..." % catalog.id)
        installed_solutions_dict[catalog.id] = catalog.list_installed()

    return installed_solutions_dict


def get_configuration():
    return HipsConfiguration()
