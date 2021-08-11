from pathlib import Path

from album.core import load
from album.core.concept.singleton import Singleton
# classes and methods
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.catalog_index import CatalogIndex
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy_folder
from album.core.utils.operations.resolve_operations import get_attributes_from_string, _check_file_or_url, \
    check_requirement, _load_solution, clean_resolve_tmp
from album_runner import logging

module_logger = logging.get_active_logger


class CatalogManager(metaclass=Singleton):
    """The Album Catalog Collection class.

    An album framework installation instance can hold arbitrarily many catalogs. This class holds all configured
    catalogs in memory and is mainly responsible to resolve (look up) solutions in all these catalogs.
    It is not responsible for resolving local paths and files or remembering what is already installed!
    Please use the resolve manager for this!
    Additionally, catalogs can be configured via this class.

     Attributes:
         configuration:
            The configuration of the album framework instance.

    """
    # Singletons
    migration_manager = None
    catalog_collection = None
    configuration = None
    tmp_cache_dir = None

    def __init__(self):
        super().__init__()
        self.setup()

    # necessary for server-test-architecture (see class TestServer - AlbumServer object)
    def setup(self):
        self.configuration = Configuration()
        self.tmp_cache_dir = self.configuration.cache_path_tmp
        self.migration_manager = MigrationManager()
        self._load_or_create_collection()

    def _load_or_create_collection(self):
        collection_meta = self.configuration.get_collection_meta_dict()
        newly_created = not self.configuration.get_collection_db_path().exists()
        self.catalog_collection = self.migration_manager.migrate_or_create_collection(
            path=self.configuration.get_collection_db_path(),
            initial_name=DefaultValues.catalog_collection_name.value,
            initial_version=collection_meta["catalog_collection_version"]
        )
        if newly_created:
            self.create_local_catalog()
            self.add_initial_catalogs()

    def create_local_catalog(self):
        catalogs = self.configuration.get_initial_catalogs()
        name = DefaultValues.local_catalog_name.value
        local_path = catalogs[name]
        self.create_new_catalog(local_path, name)

    def add_initial_catalogs(self):
        catalogs = self.configuration.get_initial_catalogs()
        for catalog in catalogs.keys():
            self.add_catalog_to_collection(catalogs[catalog])

    def get_catalog_by_id(self, catalog_id):
        """Looks up a catalog by its id and returns it."""
        catalog = self.catalog_collection.get_catalog(catalog_id)
        if not catalog:
            raise LookupError("Catalog with id \"%s\" not configured!" % catalog_id)
        return self._as_catalog(catalog)

    def get_catalog_by_src(self, src):
        """Returns the catalog object of a given url if configured."""
        catalog_dict = self.catalog_collection.get_catalog_by_src(src)
        if not catalog_dict:
            raise LookupError("Catalog with src \"%s\" not configured!" % src)
        return self._as_catalog(catalog_dict)

    def get_catalog_by_name(self, name):
        """Looks up a catalog by its id and returns it."""
        catalog_dict = self.catalog_collection.get_catalog_by_name(name)
        if not catalog_dict:
            raise LookupError("Catalog with name \"%s\" not configured!" % name)
        return self._as_catalog(catalog_dict)

    def get_catalog_by_path(self, path):
        """Looks up a catalog by its id and returns it."""
        catalog_dict = self.catalog_collection.get_catalog_by_path(path)
        if not catalog_dict:
            raise LookupError("Catalog with path \"%s\" not configured!" % path)
        return self._as_catalog(catalog_dict)

    def get_catalogs(self):
        """Creates the catalog objects from the catalogs specified in the configuration."""
        catalogs = []
        catalog_list = self.catalog_collection.get_all_catalogs()

        for catalog_entry in catalog_list:
            catalogs.append(self._as_catalog(catalog_entry))

        return catalogs

    def get_local_catalog(self):
        """Returns the first local catalog in the configuration (Reads db table from top)."""
        local_catalog = None
        for catalog in self.get_catalogs():
            if catalog.is_local:
                local_catalog = catalog
                break

        if local_catalog is None:
            raise RuntimeError("Misconfiguration of catalogs. There must be at least one local catalog!")

        return local_catalog

    def resolve_in_catalogs(self, solution_attr):
        """Resolves a dictionary holding solution attributes (group, name, version, etc.) and
        returns the path to the solution.py file on the current system.

        Args:
            solution_attr:
                Dictionary holding the attributes defining a solution (group, name, version are required).

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        # resolve local catalog first!
        local_catalog = self.get_local_catalog()
        path_to_solution = self._resolve_in_catalog(local_catalog, solution_attr)

        if path_to_solution:
            return {
                "path": path_to_solution,
                "catalog": local_catalog
            }
        else:
            # resolve in order of catalogs specified in config file
            for catalog in self.get_catalogs():
                if catalog.name == local_catalog.name:
                    continue  # skip local catalog as it already has been checked

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
            check_requirement(solution_attr)

            group = solution_attr["group"]
            name = solution_attr["name"]
            version = solution_attr["version"]

            path_to_solution = self.resolve(catalog, group, name, version)

        return path_to_solution

    def resolve(self, catalog, group, name, version):
        """Resolves (also: finds, looks up) a solution in the catalog, returning the absolute path to the solution file.

        Args:
            catalog:
                The catalog object where the solution belongs to.
            group:
                The group where the solution belongs to.
            name:
                The name of the solution
            version:
                The version of the solution

        Returns: the path to the solution file.

        """
        solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(catalog.catalog_id, name, version, group)

        if solution_entry:
            path_to_solution = catalog.get_solution_file(group, name, version)

            return path_to_solution

        return None  # could not resolve

    def add_to_local_catalog(self, active_solution, path):
        """Force adds the installation to the local catalog to be cached for running"""
        self.add_or_replace_solution_in_collection(self.get_local_catalog(), active_solution, path)
        clean_resolve_tmp(self.tmp_cache_dir)

    def add_or_replace_solution_in_collection(self, catalog, active_solution, path):
        self.catalog_collection.add_or_replace_solution(catalog.catalog_id, active_solution["group"], active_solution["name"],
                                                active_solution["version"], active_solution.get_deploy_dict())
        # get the install location
        install_location = catalog.get_solution_path(
            active_solution.group, active_solution.name, active_solution.version
        )
        copy_folder(path, install_location, copy_root_folder=False)

    def resolve_doi(self, doi):
        """Resolves an album via doi. Returns the absolute path to the solution.

        Args:
            doi:
                The doi of the solution

        Returns:
            Absolute path to the solution file.

        """
        solution_entry = self.catalog_collection.get_solution_by_doi(doi)

        if solution_entry:
            path_to_solution = self.catalog_collection.get_catalog(solution_entry["catalog_id"]).get_solution_file(
                solution_entry["group"],
                solution_entry["name"],
                solution_entry["version"]
            )

            return path_to_solution

        return None  # could not resolve

    @staticmethod
    def create_new_catalog(local_path, name):
        if not local_path.exists():
            local_path.mkdir(parents=True)
        with open(local_path.joinpath(DefaultValues.catalog_index_file_json.value), 'w') as meta:
            meta.writelines("{\"name\": \"" + name + "\", \"version\": \"" + CatalogIndex.version + "\"}")

    @staticmethod
    def _update(catalog: Catalog):
        r = catalog.refresh_index()
        module_logger().info('Updated catalog %s!' % catalog.name)

        return r

    def update_by_name(self, catalog_name):
        catalog = self.get_catalog_by_name(catalog_name)

        return self._update(catalog)

    def update_all(self):
        catalog_r = []
        for catalog in self.get_catalogs():
            try:
                r = self._update(catalog)
                catalog_r.append(r)
            except Exception:
                module_logger().warning("Failed to update catalog %s!" % catalog.name)
                catalog_r.append(False)
                pass

        return catalog_r

    def update_any(self, catalog_name=None):
        if catalog_name:
            self.update_by_name(catalog_name)
        else:
            self.update_all()

    def add_catalog_to_collection(self, identifier):
        """ Adds a catalog."""
        catalog = self._create_catalog_from_src(identifier)
        if not catalog.is_cache():
            self.migration_manager.convert_catalog(catalog)
        self.add_catalog_to_collection_index(catalog)
        self._create_catalog_cache_if_missing(catalog)
        module_logger().info('Added catalog %s!' % identifier)
        return catalog

    def add_catalog_to_collection_index(self, catalog: Catalog) -> int:
        catalog.catalog_id = self.catalog_collection.insert_catalog(catalog.name, str(catalog.src), str(catalog.path),
                                               int(catalog.is_deletable))
        if not catalog.is_cache():
            self._add_catalog_solutions_to_collection_index(catalog)
        return catalog.catalog_id

    def _add_catalog_solutions_to_collection_index(self, catalog):
        if not catalog.catalog_index:
            catalog.load_index()
        solutions = catalog.catalog_index.get_all_solutions()
        for solution in solutions:
            self.catalog_collection.add_or_replace_solution(catalog.catalog_id, solution["group"], solution["name"],
                                                            solution["version"], solution)

    def _create_catalog_from_src(self, src):
        catalog_meta_information = Catalog.retrieve_catalog_meta_information(src)
        catalog_path = self.configuration.get_cache_path_catalog(catalog_meta_information["name"])
        catalog = Catalog(None, catalog_meta_information["name"], catalog_path, src=src)
        return catalog

    @staticmethod
    def _create_catalog_cache_if_missing(catalog):
        if not catalog.path.exists():
            catalog.path.mkdir(parents=True)

    def remove_catalog_from_collection_by_path(self, path):
        catalog_dict = self.catalog_collection.get_catalog_by_path(path)
        if not catalog_dict:
            module_logger().warning(f"Cannot remove catalog, catalog with path {path} not found!")
            return None

        catalog_to_remove = self._as_catalog(catalog_dict)

        if not catalog_to_remove:
            module_logger().warning("Cannot remove catalog with path \"%s\"! Not configured!" % str(path))
            return

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_entire_catalog(catalog_to_remove.catalog_id)

        return catalog_to_remove

    def remove_catalog_from_collection_by_name(self, name):
        catalog_dict = self.catalog_collection.get_catalog_by_name(name)

        if not catalog_dict:
            raise LookupError("Cannot remove catalog with name \"%s\", not found!" % str(name))

        catalog_to_remove = self._as_catalog(catalog_dict)

        if not catalog_to_remove:
            raise LookupError("Cannot remove catalog with name \"%s\"! Not configured!" % str(name))

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_entire_catalog(catalog_to_remove.catalog_id)

        return catalog_to_remove

    def remove_catalog_from_collection_by_src(self, src):

        catalog_to_remove = self._as_catalog(self.catalog_collection.get_catalog_by_src(src))

        if not catalog_to_remove:
            module_logger().warning("Cannot remove catalog with source \"%s\"! Not configured!" % str(src))
            return

        if not catalog_to_remove.is_deletable:
            module_logger().warning("Cannot remove catalog! Marked as not deletable! Will do nothing...")
            return None

        self.catalog_collection.remove_entire_catalog(catalog_to_remove.catalog_id)

        return catalog_to_remove

    def remove_solution(self, catalog, solution):
        self.catalog_collection.remove_solution(catalog.catalog_id, solution['group'], solution['name'], solution['version'])

    def resolve_require_installation_and_load(self, str_input):
        """Resolves an input. Expects solution to be installed.

        Args:
            str_input:

        Returns:

        """
        resolve, solution_entry = self._resolve(str_input)

        if not solution_entry or not solution_entry["installed"]:
            raise LookupError("Solution seems not to be installed! Please install solution first!")

        active_solution = load(resolve["path"])

        active_solution.set_environment(resolve["catalog"].name)

        return [resolve, active_solution]

    def resolve_download_and_load(self, str_input):
        """

        Args:
            str_input:
                What to resolve. Either path, doi, group:name:version or dictionary

        Returns:
            list with resolve result and loaded album.

        """

        resolve, solution_entry = self._resolve(str_input)

        if not Path(resolve["path"]).exists():
            resolve["catalog"].retrieve_solution(
                solution_entry["group"], solution_entry["name"], solution_entry["version"]
            )

        active_solution = _load_solution(resolve)
        return [resolve, active_solution]

    def resolve_dependency_and_load(self, solution_attrs, load_solution=True):
        """Resolves a dependency, expecting it to be installed (live inside a catalog)

        Args:
            solution_attrs:
                The solution attributes to resolve for. must hold grp, name, version.
            load_solution:
                Whether to immediately load the solution or not.
        Returns:
            resolving dictionary.

        """
        # check if solution is installed
        solution_entries = self.catalog_collection.get_solutions_by_grp_name_version(
            solution_attrs["group"], solution_attrs["name"], solution_attrs["version"]
        )

        if solution_entries and len(solution_entries) > 1:
            module_logger().warning("Found multiple entries of dependency %s:%s:%s "
                                    % (solution_attrs["group"], solution_attrs["name"], solution_attrs["version"]))

        if not solution_entries or not solution_entries[0]["installed"]:
            raise LookupError("Dependency %s:%s:%s seems not to be installed! Please install solution first!"
                              % (solution_attrs["group"], solution_attrs["name"], solution_attrs["version"]))

        first_solution = solution_entries[0]

        catalog = self.get_catalog_by_id(first_solution["catalog_id"])

        resolve = {
            "path": catalog.get_solution_file(
                first_solution["group"], first_solution["name"], first_solution["version"]
            ),
            "catalog": catalog
        }

        active_solution = None

        if load_solution:
            active_solution = _load_solution(resolve)

        return [resolve, active_solution]

    def _resolve(self, str_input):
        # always first resolve outside any catalog
        path = _check_file_or_url(str_input, self.configuration.cache_path_tmp)
        if path:
            solution_entry = self.search_local_file(path)  # requires loading

            catalog = self.get_local_catalog()
            resolve = {
                "path": path,
                "catalog": catalog,
            }
        else:
            solution_entry = self.search(str_input)

            if not solution_entry:
                raise LookupError("Solution cannot be resolved in any catalog!")

            catalog = self.get_catalog_by_id(solution_entry["catalog_id"])

            resolve = {
                "path": catalog.get_solution_file(
                    solution_entry["group"], solution_entry["name"], solution_entry["version"]
                ),
                "catalog": catalog
            }

        return [resolve, solution_entry]

    def search_local_file(self, path):
        active_solution = load(path)
        solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
            self.get_local_catalog().catalog_id,
            active_solution["group"],
            active_solution["name"],
            active_solution["version"]
        )

        return solution_entry

    def search(self, str_input):
        attrs = get_attributes_from_string(str_input)

        solution_entry = None
        if "doi" in attrs:  # case doi
            solution_entry = self.catalog_collection.get_solution_by_doi(attrs["doi"])
        else:
            if "catalog" not in attrs:
                solution_entry = self._search_in_local_catalog(attrs)  # resolve in local catalog first!

            if not solution_entry:
                if "catalog" in attrs:  # resolve in specific catalog
                    catalog_id = self.get_catalog_by_name(attrs["catalog"]).catalog_id
                    solution_entry = self._search_in_specific_catalog(catalog_id, attrs)
                else:
                    solution_entries = self._search_in_catalogs(attrs)  # resolve anywhere

                    if solution_entries and len(solution_entries) > 1:
                        module_logger().warning("Found several solutions... taking the first one! ")

                    if solution_entries:
                        solution_entry = solution_entries[0]

        return solution_entry

    def _search_in_local_catalog(self, attrs):
        return self._search_in_specific_catalog(self.get_local_catalog().catalog_id, attrs)

    def _search_in_specific_catalog(self, catalog_id, attrs):
        check_requirement(attrs)
        group = attrs["group"]
        name = attrs["name"]
        version = attrs["version"]
        solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog_id, group, name, version)
        return solution_entry

    def _search_in_catalogs(self, attrs):
        check_requirement(attrs)
        group = attrs["group"]
        name = attrs["name"]
        version = attrs["version"]

        solution_entries = self.catalog_collection.get_solutions_by_grp_name_version(group, name, version)

        return solution_entries if solution_entries else None

    def resolve_dependency(self, dependency, update=True):
        """Resolves the album and returns the path to the solution.py file on the current system.
        Throws error if not resolvable!"""

        r = self.resolve(dependency, update)

        if not r:
            raise ValueError("Could not resolve solution: %s" % dependency)

        return r

    def get_index_as_dict(self):
        catalogs = self.catalog_collection.get_all_catalogs()
        for catalog in catalogs:
            catalog["solutions"] = self.catalog_collection.get_solutions_by_catalog(catalog["catalog_id"])
        return {
            "catalogs": catalogs
        }

    def get_catalogs_as_dict(self):
        return {
            "catalogs": self.catalog_collection.get_all_catalogs()
        }

    @staticmethod
    def _as_catalog(catalog_dict):
        return Catalog(catalog_dict['catalog_id'], catalog_dict['name'], catalog_dict['path'], catalog_dict['src'], bool(catalog_dict['deletable']))
