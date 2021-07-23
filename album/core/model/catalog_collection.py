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

    def __init__(self):
        super().__init__()
        self.config_file_path = None
        self.config_file_dict = None
        self.catalogs = None
        self.local_catalog = None
        self.setup()

    def setup(self):
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
        """Returns the catalog object of a given url if configured."""
        for catalog in self.catalogs:
            if catalog.src == url:
                if not catalog.is_local:
                    return catalog
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

    def resolve(self, solution_attr, update=True):
        """Resolves a dictionary holding solution attributes (group, name, version, etc.) and
        returns the path to the solution.py file on the current system.

        Args:
            solution_attr:
                Dictionary holding the attributes defining a solution (group, name, version are required).
            update:
                Boolean to indicate whether to update the catalog before resolving or not.

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        # resolve local catalog first!
        path_to_solution = self._resolve_in_catalog(self.local_catalog, solution_attr)

        if path_to_solution:
            return {
                "path": path_to_solution,
                "catalog": self.local_catalog
            }
        else:
            # resolve in order of catalogs specified in config file
            for catalog in self.catalogs:
                if catalog.id == self.local_catalog.id:
                    continue  # skip local catalog as it already has been checked

                # update if necessary and possible
                if not catalog.is_local and update:
                    catalog.refresh_index()

                path_to_solution = self._resolve_in_catalog(catalog, solution_attr)

                if path_to_solution:
                    return {
                        "path": path_to_solution,
                        "catalog": catalog
                    }

        return None  # not resolvable

    def _resolve_in_catalog(self, catalog, solution_attr):
        if "doi" in solution_attr.keys():
            raise NotImplementedError
        else:
            self._check_requirement(solution_attr)

            group = solution_attr["group"]
            name = solution_attr["name"]
            version = solution_attr["version"]

            path_to_solution = catalog.resolve(group, name, version)

        return path_to_solution

    @staticmethod
    def _check_requirement(solution_attr):
        if not all([k in solution_attr.keys() for k in ["name", "version", "group"]]):
            raise ValueError("Cannot resolve dependency! Either a DOI or name, group and version must be specified!")

    def resolve_dependency(self, dependency, update=True):
        """Resolves the album and returns the path to the solution.py file on the current system.
        Throws error if not resolvable!"""

        r = self.resolve(dependency, update)

        if not r:
            raise ValueError("Could not resolve solution: %s" % dependency)

        return r

    def resolve_directly(self, catalog_id, group, name, version, update=True):
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
            update:
                Boolean to indicate whether to update the catalog before resolving or not.

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        for catalog in self.catalogs:
            if catalog.id == catalog_id:
                # update if necessary and possible
                if not catalog.is_local and update:
                    catalog.refresh_index()

                path_to_solution = catalog.resolve(group, name, version)

                if path_to_solution:
                    return {
                        "path": path_to_solution,
                        "catalog": catalog
                    }
        return None


