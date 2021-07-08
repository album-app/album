from pathlib import Path
from zipfile import ZipFile

from album.core import load
from album.core.concept.singleton import Singleton
from album.core.model.catalog_collection import CatalogCollection
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import unzip_archive, copy, copy_folder, force_remove, \
    create_path_recursively, rand_folder_name
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

    def clean_resolve_tmp(self):
        """Cleans the temporary directory which might have been used during resolving."""
        force_remove(self.tmp_cache_dir)
        create_path_recursively(self.tmp_cache_dir)

    def resolve_and_load(self, str_input, mode="c"):
        """Resolves in two ways: either mode "a": returns first resolving, or mode "c", resolves first locally, then
        in a catalog.

        Args:
            str_input:
                What to resolve. Either path, doi, group:name:version or dictionary
            mode:
                c - resolve locally and if found in catalogs
                a - resolve everywhere, give back first found match

        Returns:
            list with resolve result and loaded album.

        """
        download_solution = True if mode == "a" else False
        resolve_local = None

        # always first resolve outside any catalog
        resolve_local = self._resolve_outside_catalog(str_input)

        if resolve_local:
            active_solution = load(resolve_local["path"])

            if mode != "a":
                # found outside, now we need to find it in a catalog
                r_input = ":".join([active_solution["group"], active_solution["name"], active_solution["version"]])
                resolve_dict = self.catalog_collection.resolve_from_str(r_input, download_solution)

                # overwrite path to already installed solution file
                resolve_dict["path"] = resolve_local["path"]

                active_solution.set_environment(resolve_dict["catalog"].id)

                return [resolve_dict, active_solution]

            else:
                active_solution.set_environment(self.catalog_collection.local_catalog.id)
                return [resolve_local, active_solution]
        else:
            resolve_catalog = self.catalog_collection.resolve_from_str(str_input, download_solution)

            active_solution = load(resolve_catalog["path"])

            # init the album environment
            active_solution.set_environment(resolve_catalog["catalog"].id)

            return [resolve_catalog, active_solution]

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
        resolve_catalog = self.catalog_collection.resolve_dependency(
            solution_attrs, download=False
        )

        active_solution = None

        if load_solution:
            active_solution = load(resolve_catalog["path"])

            # init the album environment
            active_solution.set_environment(resolve_catalog["catalog"].id)

        return [resolve_catalog, active_solution]

    def _resolve_outside_catalog(self, path):
        """Resolves a path or url. Independent of catalogs."""
        if is_url(path):
            p = download(str(path), base=self.configuration.cache_path_tmp)
        else:
            p = Path(path)  # no problems with urls or symbols not allowed for paths!

        if p.exists():
            target_folder = self.tmp_cache_dir.joinpath(rand_folder_name())
            if p.is_file():  # zip or file
                if p.suffix == ".zip" and not ZipFile(p).testzip():  # zip file
                    p = unzip_archive(p, target_folder)
                    p = p.joinpath(DefaultValues.solution_default_name.value)
                else:  # python file
                    p = copy(p, target_folder.joinpath(DefaultValues.solution_default_name.value))
            elif p.is_dir():  # unzipped zip
                p = copy_folder(p, target_folder, copy_root_folder=False)
                p = p.joinpath(DefaultValues.solution_default_name.value)

            return {
                "path": p,
                "catalog": None
            }

        return None
