from pathlib import Path
from typing import Optional

from album.core.model.collection_index import CollectionIndex
from album.core.utils.operations.file_operations import write_dict_to_json

from album.core import load
from album.core.concept.singleton import Singleton
# classes and methods
from album.core.controller.catalog_handler import CatalogHandler
from album.core.controller.migration_manager import MigrationManager
from album.core.controller.solution_handler import SolutionHandler
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.resolve_operations import clean_resolve_tmp, _check_file_or_url, _load_solution, \
    get_attributes_from_string, dict_to_group_name_version, solution_to_group_name_version
from album_runner import logging

module_logger = logging.get_active_logger


class CollectionManager(metaclass=Singleton):
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
    catalog_collection = None
    configuration = None
    tmp_cache_dir = None

    def __init__(self):
        super().__init__()
        self.configuration = Configuration()
        if not self.configuration.is_setup:
            self.configuration.setup()
        self.tmp_cache_dir = self.configuration.cache_path_tmp
        self.migration_manager = MigrationManager()
        self._load_or_create_collection()

    def _load_or_create_collection(self):
        collection_meta = self.configuration.get_collection_meta_dict()
        newly_created = not self.configuration.get_collection_db_path().exists()
        if collection_meta:
            collection_version = collection_meta["catalog_collection_version"]
        else:
            if newly_created:
                collection_version = CollectionIndex.version
                self.write_version_to_yml(self.configuration.get_collection_meta_path(), "my-collection", collection_version)
            else:
                raise RuntimeError("Album collection database file found, but no meta file specifying the database version.")
        self.catalog_collection = self.migration_manager.migrate_or_create_collection(
            path=self.configuration.get_collection_db_path(),
            initial_name=DefaultValues.catalog_collection_name.value,
            initial_version=collection_version
        )
        self.solution_handler = SolutionHandler(self.catalog_collection)
        self.catalog_handler = CatalogHandler(self.configuration, self.catalog_collection, self.solution_handler)
        if newly_created:
            self.catalog_handler.create_local_catalog()
            self.catalog_handler.add_initial_catalogs()

    def catalogs(self) -> CatalogHandler:
        return self.catalog_handler

    def solutions(self) -> SolutionHandler:
        return self.solution_handler

    def add_solution_to_local_catalog(self, active_solution, path):
        """Force adds the installation to the local catalog to be cached for running"""
        self.solution_handler.add_or_replace(self.catalog_handler.get_local_catalog(), active_solution, path)
        clean_resolve_tmp(self.tmp_cache_dir)

    def get_index_as_dict(self):
        catalogs = self.catalog_collection.get_all_catalogs()
        for catalog in catalogs:
            catalog["solutions"] = self.catalog_collection.get_solutions_by_catalog(catalog["catalog_id"])
        return {
            "catalogs": catalogs
        }

    def resolve_require_installation_and_load(self, str_input) -> ResolveResult:
        """Resolves an input. Expects solution to be installed.

        Args:
            str_input:

        Returns:

        """
        resolve_result = self._resolve(str_input)

        if not resolve_result.solution_attrs or not resolve_result.solution_attrs["installed"]:
            raise LookupError("Solution seems not to be installed! Please install solution first!")

        active_solution = load(resolve_result.path)

        active_solution.set_environment(resolve_result.catalog.name)
        resolve_result.active_solution = active_solution

        return resolve_result

    def resolve_download_and_load(self, str_input) -> ResolveResult:
        """

        Args:
            str_input:
                What to resolve. Either path, doi, group:name:version or dictionary

        Returns:
            list with resolve result and loaded album.

        """

        resolve_result = self._resolve(str_input)

        if not Path(resolve_result.path).exists():
            resolve_result.catalog.retrieve_solution(
                dict_to_group_name_version(resolve_result.solution_attrs)
            )

        resolve_result.active_solution = _load_solution(resolve_result)
        return resolve_result

    def resolve_dependency_require_installation_and_load(self, solution_attrs) -> ResolveResult:
        """Resolves a dependency, expecting it to be installed (live inside a catalog), and loads it

        Args:
            solution_attrs:
                The solution attributes to resolve for. must hold grp, name, version.
        Returns:
            resolve result.

        """
        resolve_result = self.resolve_dependency_require_installation(solution_attrs)
        resolve_result.active_solution = _load_solution(resolve_result)
        return resolve_result

    def resolve_dependency_require_installation(self, solution_attrs) -> ResolveResult:
        """Resolves a dependency, expecting it to be installed (live inside a catalog)

        Args:
            solution_attrs:
                The solution attributes to resolve for. must hold grp, name, version.
        Returns:
            resolve result.

        """
        resolve_result = self.resolve_dependency(solution_attrs)
        if not resolve_result.solution_attrs["installed"]:
            raise LookupError("Dependency %s seems not to be installed! Please install solution first!"
                              % (dict_to_group_name_version(solution_attrs)))

        return resolve_result

    def resolve_dependency(self, solution_attrs) -> ResolveResult:
        """Resolves the album and returns the path to the solution.py file on the current system.
        Throws error if not resolvable!"""
        solution_entries = self.catalog_collection.get_solutions_by_grp_name_version(
            dict_to_group_name_version(solution_attrs))
        if solution_entries and len(solution_entries) > 1:
            module_logger().warning("Found multiple entries of dependency %s "
                                    % (dict_to_group_name_version(solution_attrs)))
        if not solution_entries or len(solution_entries) == 0:
            raise LookupError("Could not resolve dependency: %s" % dict_to_group_name_version(solution_attrs))
        first_solution = solution_entries[0]
        catalog = self.catalog_handler.get_by_id(first_solution["catalog_id"])
        path = catalog.get_solution_file(dict_to_group_name_version(first_solution))
        resolve_result = ResolveResult(path=path, catalog=catalog, solution_attrs=first_solution)
        return resolve_result

    def _resolve(self, str_input):
        # always first resolve outside any catalog
        path = _check_file_or_url(str_input, self.configuration.cache_path_tmp)
        if path:
            solution_entry = self._search_local_file(path)  # requires loading

            catalog = self.catalog_handler.get_local_catalog()
            resolve = ResolveResult(path=path, catalog=catalog, solution_attrs=solution_entry)
        else:
            solution_entry = self._search(str_input)

            if not solution_entry:
                raise LookupError("Solution cannot be resolved in any catalog!")

            catalog = self.catalog_handler.get_by_id(solution_entry["catalog_id"])

            solution_file = catalog.get_solution_file(dict_to_group_name_version(solution_entry))
            resolve = ResolveResult(path=solution_file, catalog=catalog, solution_attrs=solution_entry)

        return resolve

    def _search_local_file(self, path) -> Optional[dict]:
        active_solution = load(path)
        if active_solution:
            solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
                self.catalog_handler.get_local_catalog().catalog_id,
                solution_to_group_name_version(active_solution)
            )

            return solution_entry
        else:
            return None

    def _search(self, str_input) -> dict:
        attrs = get_attributes_from_string(str_input)

        solution_entry = None
        if "doi" in attrs:  # case doi
            solution_entry = self.catalog_collection.get_solution_by_doi(attrs["doi"])
        else:
            if "catalog" not in attrs:
                solution_entry = self._search_in_local_catalog(attrs)  # resolve in local catalog first!

            if not solution_entry:
                if "catalog" in attrs:  # resolve in specific catalog
                    catalog_id = self.catalog_handler.get_by_name(attrs["catalog"]).catalog_id
                    solution_entry = self._search_in_specific_catalog(catalog_id, attrs)
                else:
                    solution_entries = self._search_in_catalogs(attrs)  # resolve anywhere

                    if solution_entries and len(solution_entries) > 1:
                        module_logger().warning("Found several solutions... taking the first one! ")

                    if solution_entries:
                        solution_entry = solution_entries[0]

        return solution_entry

    def _search_in_local_catalog(self, attrs):
        return self._search_in_specific_catalog(self.catalog_handler.get_local_catalog().catalog_id, attrs)

    def _search_in_specific_catalog(self, catalog_id, attrs):
        solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog_id, dict_to_group_name_version(attrs))
        return solution_entry

    def _search_in_catalogs(self, attrs):
        solution_entries = self.catalog_collection.get_solutions_by_grp_name_version(dict_to_group_name_version(attrs))

        return solution_entries if solution_entries else None

    @staticmethod
    def write_version_to_yml(path, name, version) -> None:
        write_dict_to_json(path, {
            "catalog_collection_name": name,
            "catalog_collection_version": version
        })
