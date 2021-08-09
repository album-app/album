import errno
import os
import re
import sys
from pathlib import Path

from album.core import load
from album.core.concept.singleton import Singleton
from album.core.controller.catalog_manager import CatalogManager
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
    catalog_manager = None

    def __init__(self):
        self.catalog_manager = CatalogManager()
        self.configuration = self.catalog_manager.configuration
        self.tmp_cache_dir = self.catalog_manager.configuration.cache_path_tmp
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

        resolve = self._resolve(str_input)
        active_solution = self._load_solution(resolve)
        return [resolve, active_solution]

    def resolve_download_load(self, str_input):
        """

        Args:
            str_input:
                What to resolve. Either path, doi, group:name:version or dictionary

        Returns:
            list with resolve result and loaded album.

        """

        resolve = self._resolve_and_download(str_input)
        active_solution = self._load_solution(resolve)
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

        resolve_catalog = self.catalog_manager.resolve_directly(
            solution_installed[0]["catalog_id"],
            solution_attrs["group"],
            solution_attrs["name"],
            solution_attrs["version"]
        )

        active_solution = None

        if load_solution:
            active_solution = self._load_solution(resolve_catalog)

        return [resolve_catalog, active_solution]

    def _resolve(self, str_input):
        # always first resolve outside any catalog
        path = self._check_file_or_url(str_input)
        if path:
            catalog = self.catalog_manager.local_catalog
            resolve = {
                "path": path,
                "catalog": catalog
            }

        else:
            attrs = self.get_attributes_from_string(str_input)
            resolve = self.catalog_manager.resolve(attrs)
            if not resolve:
                raise LookupError("Solution cannot be resolved in any catalog!")
        return resolve

    def _resolve_and_download(self, str_input):
        resolve = self._resolve(str_input)
        if not Path(resolve["path"]).exists():
            attrs = self.get_attributes_from_string(str_input)
            resolve["catalog"].download_solution(attrs["group"], attrs["name"], attrs["version"])
        return resolve

    def _resolve_local_file(self, path):
        active_solution = load(path)
        solution_installed = self.solution_db.get_solutions_by_grp_name_version(
            active_solution["group"], active_solution["name"], active_solution["version"]
        )

        if not solution_installed:
            raise LookupError("Solution seems not to be installed! Please install solution first!")

        catalog = self.catalog_manager.get_catalog_by_id(solution_installed[0]["catalog_id"])

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
        if "catalog" in attrs_dict:
            solution_installed = self.solution_db.get_solution_by_catalog_grp_name_version(
                attrs_dict["catalog"], attrs_dict["group"], attrs_dict["name"], attrs_dict["version"]
            )
        else:
            solution_installed = self.solution_db.get_solutions_by_grp_name_version(
                attrs_dict["group"], attrs_dict["name"], attrs_dict["version"]
            )
            if solution_installed and len(solution_installed) > 0:
                solution_installed = solution_installed[0]
            else:
                solution_installed = None

        if not solution_installed:
            raise LookupError("Solution seems not to be installed! Please install solution first!")

        resolve = self.catalog_manager.resolve_directly(
            solution_installed["catalog_id"], attrs_dict["group"], attrs_dict["name"], attrs_dict["version"]
        )

        active_solution = load(resolve["path"])

        active_solution.set_environment(solution_installed["catalog_id"])

        return [resolve, active_solution]

    def _check_file_or_url(self, path):
        """Resolves a path or url. Independent of catalogs."""
        if is_url(path):
            p = download(str(path), base=self.configuration.cache_path_tmp)
        elif self.is_pathname_valid(path):
            p = Path(path)  # no problems with urls or symbols not allowed for paths!
        else:
            return None

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
                    cgnv: <catalog>:<group>:<name>:<version> of a solution
                    url: any url pointing to a solution file

        Returns:
            Dictionary holding the path to the solution and the catalog the solution has been resolved in.

        """
        attrs_dict = self.get_doi_from_input(str_input)
        if not attrs_dict:
            attrs_dict = self.get_gnv_from_input(str_input)
            if not attrs_dict:
                attrs_dict = self.get_cgnv_from_input(str_input)
                if not attrs_dict:
                    raise ValueError(
                        "Invalid input format! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> or "
                        "<group>:<name>:<version> or <catalog>:<group>:<name>:<version> or point to a valid file! Aborting...")
        module_logger().debug("Parsed %s from the input... " % attrs_dict)
        return attrs_dict

    @staticmethod
    def _load_solution(resolve):
        active_solution = load(resolve["path"])
        # init the album environment
        active_solution.set_environment(resolve["catalog"].id)
        return active_solution

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
    def get_cgnv_from_input(str_input: str):
        """Parses Catalog, Group, Name, Version from input, separated by ":". """
        s = re.search('^([^:]+):([^:]+):([^:]+):([^:]+)$', str_input)

        if s:
            return {
                "catalog": s.group(1),
                "group": s.group(2),
                "name": s.group(3),
                "version": s.group(4)
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

    @staticmethod
    def is_pathname_valid(pathname: str) -> bool:
        '''
        `True` if the passed pathname is a valid pathname for the current OS;
        `False` otherwise.
        source: https://stackoverflow.com/a/34102855
        '''
        # Windows-specific error code indicating an invalid pathname.
        # Sadly, Python fails to provide the following magic number for us.
        ERROR_INVALID_NAME = 123
        # If this pathname is either not a string or is but is empty, this pathname
        # is invalid.
        try:
            if not isinstance(pathname, str) or not pathname:
                return False

            # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
            # if any. Since Windows prohibits path components from containing `:`
            # characters, failing to strip this `:`-suffixed prefix would
            # erroneously invalidate all valid absolute Windows pathnames.
            _, pathname = os.path.splitdrive(pathname)

            # Directory guaranteed to exist. If the current OS is Windows, this is
            # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
            # environment variable); else, the typical root directory.
            root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
                if sys.platform == 'win32' else os.path.sep
            assert os.path.isdir(root_dirname)  # ...Murphy and her ironclad Law

            # Append a path separator to this directory if needed.
            root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

            # Test whether each path component split from this pathname is valid or
            # not, ignoring non-existent and non-readable path components.
            for pathname_part in pathname.split(os.path.sep):
                try:
                    os.lstat(root_dirname + pathname_part)
                # If an OS-specific exception is raised, its error code
                # indicates whether this pathname is valid or not. Unless this
                # is the case, this exception implies an ignorable kernel or
                # filesystem complaint (e.g., path not found or inaccessible).
                #
                # Only the following exceptions indicate invalid pathnames:
                #
                # * Instances of the Windows-specific "WindowsError" class
                #   defining the "winerror" attribute whose value is
                #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
                #   fine-grained and hence useful than the generic "errno"
                #   attribute. When a too-long pathname is passed, for example,
                #   "errno" is "ENOENT" (i.e., no such file or directory) rather
                #   than "ENAMETOOLONG" (i.e., file name too long).
                # * Instances of the cross-platform "OSError" class defining the
                #   generic "errno" attribute whose value is either:
                #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
                #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
                except OSError as exc:
                    if hasattr(exc, 'winerror'):
                        if exc.winerror == ERROR_INVALID_NAME:
                            return False
                    elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                        return False
        # If a "TypeError" exception was raised, it almost certainly has the
        # error message "embedded NUL character" indicating an invalid pathname.
        except TypeError:
            return False
        # If no exception was raised, all path components and hence this
        # pathname itself are valid. (Praise be to the curmudgeonly python.)
        else:
            return True
        # If any other exception was raised, this is an unrelated fatal issue
        # (e.g., a bug). Permit this exception to unwind the call stack.
