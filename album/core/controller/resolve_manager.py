import re
from pathlib import Path
from zipfile import ZipFile

from album.core import load
from album.core.concept.singleton import Singleton
from album.core.model.catalog_collection import CatalogCollection
from album.core.model.default_values import DefaultValues
from album.core.model.solutions_db import SolutionsDb
from album.core.utils.operations.file_operations import unzip_archive, copy, copy_folder, force_remove, \
    create_path_recursively, rand_folder_name, check_zip
from album.core.utils.operations.url_operations import is_url, download
from album_runner import logging

module_logger = logging.get_active_logger


class ResolveManager(metaclass=Singleton):
    """Main class for resolving inputs.

    The framework is supposed to run solutions within a catalog or without. This class provides functionality
    to look up an input in all configured catalogs or tries to solve the input otherwise. Thereby remembering
    which solutions outside a catalog have already ben executed once such that they are already installed and
    can be immediately executed.

    """
    # singletons
    catalog_collection = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = CatalogCollection() if not catalog_collection else catalog_collection
        self.configuration = self.catalog_collection.configuration
        self.tmp_cache_dir = self.catalog_collection.configuration.cache_path_tmp
        self.solution_db = SolutionsDb()

    def clean_resolve_tmp(self):
        """Cleans the temporary directory which might have been used during resolving."""
        force_remove(self.tmp_cache_dir)
        create_path_recursively(self.tmp_cache_dir)

    def resolve_installed_and_load(self, str_input):
        """Resolves an input. Expects solution to be installed, thus, looking it up in the installation database.

        Args:
            str_input:

        Returns:

        """
        # always first resolve outside any catalog
        path = self._check_file_or_url(str_input)

        if path:
            resolve = self._resolve_local_file(path)
        else:
            resolve = self._resolve_from_catalog(str_input)

        return resolve

    def resolve_and_load(self, str_input):
        """

        Args:
            str_input:
                What to resolve. Either path, doi, group:name:version or dictionary

        Returns:
            list with resolve result and loaded album.

        """

        # always first resolve outside any catalog
        path = self._check_file_or_url(str_input)

        if path:
            active_solution = load(path)

            catalog = self.catalog_collection.local_catalog

            active_solution.set_environment(catalog.id)

            resolve = {
                "path": path,
                "catalog": catalog
            }

        else:
            attrs = self.get_attributes_from_string(str_input)

            resolve = self.catalog_collection.resolve(attrs, update=False)

            if not resolve:
                raise LookupError("Solution cannot be resolved in any catalog!")

            active_solution = load(resolve["path"])

            # init the album environment
            active_solution.set_environment(resolve["catalog"].id)

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
        solution_installed = self.solution_db.get_solutions_by_grp_name_version(
            solution_attrs["group"], solution_attrs["name"], solution_attrs["version"]
        )

        if not solution_installed:
            raise LookupError("Dependency %s:%s:%s seems not to be installed! Please install solution first!"
                              % (solution_attrs["group"], solution_attrs["name"], solution_attrs["version"]))

        resolve_catalog = self.catalog_collection.resolve_directly(
            solution_installed[0]["catalog_id"],
            solution_attrs["group"],
            solution_attrs["name"],
            solution_attrs["version"]
        )

        active_solution = None

        if load_solution:
            active_solution = load(resolve_catalog["path"])

            # init the album environment
            active_solution.set_environment(resolve_catalog["catalog"].id)

        return [resolve_catalog, active_solution]

    def _resolve_local_file(self, path):
        active_solution = load(path)
        solution_installed = self.solution_db.get_solutions_by_grp_name_version(
            active_solution["group"], active_solution["name"], active_solution["version"]
        )

        if not solution_installed:
            raise LookupError("Solution seems not to be installed! Please install solution first!")

        catalog = self.catalog_collection.get_catalog_by_id(solution_installed[0]["catalog_id"])

        active_solution.set_environment(catalog.id)

        return [
            {
                "path": path,
                "catalog": catalog
            },
            active_solution
        ]

    def _resolve_from_catalog(self, str_input):
        attrs_dict = self.get_attributes_from_string(str_input)
        solution_installed = self.solution_db.get_solutions_by_grp_name_version(
            attrs_dict["group"], attrs_dict["name"], attrs_dict["version"]
        )

        if not solution_installed:
            raise LookupError("Solution seems not to be installed! Please install solution first!")

        resolve = self.catalog_collection.resolve_directly(
            solution_installed[0]["catalog_id"], attrs_dict["group"], attrs_dict["name"], attrs_dict["version"]
        )

        active_solution = load(resolve["path"])

        active_solution.set_environment(solution_installed[0]["catalog_id"])

        return [resolve, active_solution]

    def _check_file_or_url(self, path):
        """Resolves a path or url. Independent of catalogs."""
        if is_url(path):
            p = download(str(path), base=self.configuration.cache_path_tmp)
        else:
            p = Path(path)  # no problems with urls or symbols not allowed for paths!

        if p.exists():
            target_folder = self.tmp_cache_dir.joinpath(rand_folder_name())
            if p.is_file():  # zip or file
                if p.suffix == ".zip" and check_zip(p):  # zip file
                    p = unzip_archive(p, target_folder)
                    p = p.joinpath(DefaultValues.solution_default_name.value)
                else:  # python file
                    p = copy(p, target_folder.joinpath(DefaultValues.solution_default_name.value))
            elif p.is_dir():  # unzipped zip
                p = copy_folder(p, target_folder, copy_root_folder=False)
                p = p.joinpath(DefaultValues.solution_default_name.value)

            return p

        return None

    def get_attributes_from_string(self, str_input: str):
        """Interprets a string input if in valid format and returns necessary attributes dictionary.

        Args:
            str_input:
                The string input. Supported formats:
                    doi:  <doi>:<prefix>/<suffix> or <prefix>/<suffix> of a solution
                    gnv: <group>:<name>:<version> of a solution
                    url: any url pointing to a solution file

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
        return attrs_dict

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
