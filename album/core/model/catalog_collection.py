import re

import validators

from album.core.concept.singleton import Singleton
# classes and methods
from album.core.model.catalog import Catalog
from album.core.model.configuration import Configuration
from album.core.utils.operations.file_operations import get_dict_from_yml, write_dict_to_yml
from album_runner import logging

module_logger = logging.get_active_logger


class CatalogCollection(metaclass=Singleton):
    """The Album Catalog Collection class.

    An album framework installation instance can hold arbitrarily many catalogs. This class collects all configured
    catalogs and is mainly responsible to resolve (look up) solutions in all these catalogs.
    Additionally, catalogs can be configured via this class.

     Attributes:
         configuration:
            The configuration of the album framework instance.

    """
    # Singletons
    configuration = None

    def __init__(self, configuration: Configuration = None):
        super().__init__()
        if configuration:
            self.configuration = configuration
        else:
            self.configuration = Configuration()
        self.config_file_path = self.configuration.configuration_file_path
        self.config_file_dict = self._load_configuration()
        self.catalogs = self._get_catalogs()
        self.local_catalog = self._get_local_catalog()

    def _create_default_configuration(self):
        """Creates the default configuration. Returns the corresponding dictionary"""
        module_logger().info("Creating default configuration...")
        config_file_dict = self.configuration.get_default_configuration()
        return config_file_dict

    def get_default_deployment_catalog(self):
        """Returns first catalog which is not local. This is used as default deployment catalog."""
        for catalog in self.catalogs:
            if not catalog.is_local:
                return catalog
        raise LookupError("No local catalog configured! Doing nothing...")

    def get_catalog_by_url(self, url):
        """Returns first catalog which is not local. This is used as default deployment catalog."""
        for catalog in self.catalogs:
            if catalog.src == url:
                if not catalog.is_local:
                    return catalog
                else:
                    raise ValueError("Cannot deploy to the catalog with url %s since it is marked local!" % url)
        raise LookupError("Catalog with URL \"%s\" not configured!" % url)

    def get_catalog_by_id(self, cat_id):
        """Looks up a catalog by its id and returns it."""
        for catalog in self.catalogs:
            if catalog.id == cat_id:
                return catalog
        raise LookupError("Catalog with ID \"%s\" not configured!" % cat_id)

    def save(self, config_file_dict=None):
        """Saves the configuration dictionary to disk. Uses the file path specified in the Configuration object."""
        module_logger().info("Saving configuration file in %s..." % self.config_file_path)
        if not config_file_dict:
            config_file_dict = self.config_file_dict

        module_logger().debug("Configuration looks like: %s..." % config_file_dict)

        return write_dict_to_yml(self.config_file_path, config_file_dict)

    def _load_configuration(self):
        """Loads a configuration.

         Either from disk (if the path specified in the Configuration object is a valid file)
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
            module_logger().debug("Try to initialize the following catalog: %s..." % catalog)

            id = self.configuration.extract_catalog_name(catalog)
            src = None
            path = catalog

            # if entry is a valid url, we set the default path
            if validators.url(catalog):
                src = catalog
                path = self.configuration.get_cache_path_catalog(id)

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

    def get_search_index(self):
        """Allow searching through all depth 3 leaves (solution entries) of all configured catalogs."""
        catalog_indices_dict = {}
        for catalog in self.catalogs:
            module_logger().debug("Load catalog leaves for catalog: %s..." % catalog.id)
            catalog_indices_dict[catalog.id] = catalog.catalog_index.get_leaves_dict_list()

        return catalog_indices_dict

    def resolve(self, solution_attr, download=True):
        """Resolves a dictionary holding solution attributes (group, name, version, etc.) and
        returns the path to the solution.py file on the current system.

        Args:
            solution_attr:
                Dictionary holding the attributes defining a solution (group, name, version are required).
            download:
                Boolean to indicate whether to download a solution from the catalog it has been found in or not.

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        file_not_found = None
        # resolve in order of catalogs specified in config file
        for catalog in self.catalogs:

            # update if necessary and possible
            if not catalog.is_local and download:
                catalog.refresh_index()

            # resolve via doi
            if "doi" in solution_attr.keys():
                path_to_solution = catalog.resolve_doi(solution_attr["doi"], download)
            else:  # resolve via group, name, version
                if not all([k in solution_attr.keys() for k in ["name", "version", "group"]]):
                    raise ValueError("Cannot resolve dependency!"
                                     " Either a DOI or name, group and version must be specified!")

                group = solution_attr["group"]
                name = solution_attr["name"]
                version = solution_attr["version"]

                try:
                    path_to_solution = catalog.resolve(group, name, version, download)
                except FileNotFoundError as e:
                    file_not_found = e
                    continue

            if not path_to_solution:
                continue

            return {
                "path": path_to_solution,
                "catalog": catalog
            }

        # only raise FileNotFound if not installed from any of the configured catalogs
        if file_not_found:
            raise file_not_found

        return None

    def resolve_dependency(self, dependency, download=True):
        """Resolves the album and returns the path to the solution.py file on the current system.
        Throws error if not resolvable!"""

        r = self.resolve(dependency, download)

        if not r:
            raise ValueError("Could not resolve solution: %s" % dependency)

        return r

    def resolve_directly(self, catalog_id, group, name, version, download=True):
        """Resolves a solution given its group, name, version only looking through a specific catalog.

        Args:
            catalog_id:
                The catalog to search the solution in.
            group:
                The group affiliation of the solution.
            name:
                The name of the solution.
            version:
                The version of the solution.
            download:
                Boolean to indicate whether to download a solution from the catalog it has been found in or not.

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        for catalog in self.catalogs:
            if catalog.id == catalog_id:
                # update if necessary and possible
                if not catalog.is_local:
                    catalog.refresh_index()
                path_to_solution = catalog.resolve(group, name, version, download)
                if not path_to_solution:
                    return None
                return {
                    "path": path_to_solution,
                    "catalog": catalog
                }
        return None

    def resolve_from_str(self, str_input: str, download=True):
        """Resolves a string input if in valid format.

        Args:
            str_input:
                The string input. Supported formats:
                    doi:  <doi>:<prefix>/<suffix> or <prefix>/<suffix> of a solution
                    gnv: <group>:<name>:<version> of a solution
                    url: any url pointing to a solution file
            download:
                Boolean to indicate whether to download a solution from the catalog it has been found in or not.

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        attrs_dict = self.get_doi_from_input(str_input)
        if not attrs_dict:
            attrs_dict = self.get_gnv_from_input(str_input)
            if not attrs_dict:
                raise ValueError(
                    "Invalid input format! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> or "
                    "<group>:<name>:<version> or point to a valid file! Aborting...")
        module_logger().debug("Parsed %s from the input... " % attrs_dict)
        return self.resolve_dependency(attrs_dict, download)

    def get_installed_solutions(self):
        """Returns all installed solutions of all catalogs configured"""
        installed_solutions_dict = {}
        for catalog in self.catalogs:
            module_logger().debug("Get installed solutions from catalog: %s..." % catalog.id)
            installed_solutions_dict[catalog.id] = catalog.list_installed()

        return installed_solutions_dict

    @staticmethod
    def get_gnv_from_input(str_input: str):
        """Parses Group, Name, Version from input, separated by ":". """
        s = re.search('^([^:]+):([^:]+):([^:]+)$', str_input)

        if s:
            return {
                "group": s.group(1),
                "name": s.group(2),
                "version": s.group(3)
            }
        return None

    @staticmethod
    def get_doi_from_input(str_input: str):
        """Parses the DOI from string input."""
        s = re.search('^(^doi:)?([^:\/]*\/[^:\/]*)$', str_input)
        if s:
            return {
                "doi": s.group(2)
            }
        return None