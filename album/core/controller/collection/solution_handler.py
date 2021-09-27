from album.core import Solution
from album.core.model.catalog_updates import ChangeType, SolutionChange
from album.core.model.collection_index import CollectionIndex
from album.core.model.identity import Identity
from album.core.utils.operations.file_operations import copy_folder
from album.core.utils.operations.resolve_operations import dict_to_identity, solution_to_identity
from album_runner import logging

module_logger = logging.get_active_logger


class SolutionHandler:

    def __init__(self, collection: CollectionIndex):
        self.catalog_collection = collection

    def get_solution_path_by_group_name_version(self, catalog, identity: Identity):
        """Resolves (also: finds, looks up) a solution in the catalog, returning the absolute path to the solution file.

        Args:
            catalog:
                The catalog object where the solution belongs to.
            identity:
                The group affiliation, name, and version of the solution.

        Returns: the path to the solution file.

        """
        solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(catalog.catalog_id, identity)

        if solution_entry:
            path_to_solution = catalog.get_solution_file(identity)

            return path_to_solution

        return None  # could not resolve

    def get_solution_path_by_doi(self, doi):
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
                dict_to_identity(solution_entry)
            )

            return path_to_solution

        return None  # could not resolve

    def add_or_replace(self, catalog, active_solution, path):
        deploy_dict = active_solution.get_deploy_dict()
        self.catalog_collection.add_or_replace_solution(catalog.catalog_id, dict_to_identity(deploy_dict), deploy_dict, self.get_solution_keys())
        # get the install location
        install_location = catalog.get_solution_path(dict_to_identity(deploy_dict))
        copy_folder(path, install_location, copy_root_folder=False)

    def add_solutions_to_catalog(self, catalog_id, solutions):
        for solution in solutions:
            self.catalog_collection.add_or_replace_solution(catalog_id, dict_to_identity(solution), solution)

    def set_uninstalled(self, catalog, solution):
        self.update_solution(catalog, solution, {"installed": 0})

    def remove_solution(self, catalog, solution):
        self.catalog_collection.remove_solution(catalog.catalog_id, solution_to_identity(solution))

    def update_solution(self, catalog, solution, attrs):
        self.catalog_collection.update_solution(catalog.catalog_id, solution_to_identity(solution), attrs, self.get_solution_keys())

    @staticmethod
    def get_solution_keys():
        keys = Solution.deploy_keys.copy()
        keys.remove("authors")
        keys.remove("tags")
        keys.remove("args")
        keys.remove("cite")
        keys.remove("covers")
        keys.append("hash")
        keys.append("installed")
        return keys

    def apply_change(self, catalog, change: SolutionChange):
        # FIXME handle other tables (tags etc)
        if change.change_type is ChangeType.ADDED:
            self.catalog_collection.add_or_replace_solution(
                catalog.catalog_id,
                change.identity,
                catalog.catalog_index.get_solution_by_group_name_version(change.identity),
                self.get_solution_keys())
        elif change.change_type is ChangeType.REMOVED:
            self.catalog_collection.remove_solution(catalog.catalog_id, change.identity)
        elif change.change_type is ChangeType.CHANGED:
            self.catalog_collection.remove_solution(catalog.catalog_id, change.identity)
            self.catalog_collection.add_or_replace_solution(
                catalog.catalog_id,
                change.identity,
                catalog.catalog_index.get_solution_by_group_name_version(change.identity),
                self.get_solution_keys())

    def set_installed(self, catalog, solution):
        self.update_solution(catalog, solution, {"installed": 1})

