from pathlib import Path
from typing import Optional, List

from album.runner.core.api.model.solution import ISolution

from album.core.api.album import IAlbum
from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.collection.collection_manager import ICollectionManager
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.resolve_result import IResolveResult
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import write_dict_to_json
from album.core.utils.operations.resolve_operations import check_file_or_url, get_attributes_from_string, \
    dict_to_coordinates, get_doi_from_input, check_doi, build_resolve_string, get_parent
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

module_logger = album_logging.get_active_logger


class CollectionManager(ICollectionManager):

    def __init__(self, album: IAlbum):
        self.album = album
        self.solution_handler = SolutionHandler(self.album)
        self.catalog_handler = CatalogHandler(self.album)
        self.catalog_collection: Optional[ICollectionIndex] = None
        self.collection_loaded = False

    def __del__(self):
        self.close()

    def close(self):
        if self.solution_handler is not None:
            del self.solution_handler
            self.solution_handler = None
        if self.catalog_handler is not None:
            del self.catalog_handler
            self.catalog_handler = None
        if self.catalog_collection is not None:
            self.catalog_collection.close()
            self.catalog_collection = None

    def get_collection_index(self) -> ICollectionIndex:
        return self.catalog_collection

    def load_or_create_collection(self):
        if self.collection_loaded:
            module_logger().warning("CollectionManager().load_or_create_collection() should only be called once.")
            return
        self.collection_loaded = True
        collection_meta = self.album.configuration().get_catalog_collection_meta_dict()
        newly_created = not self.album.configuration().get_catalog_collection_path().exists()
        if collection_meta:
            collection_version = collection_meta["catalog_collection_version"]
        else:
            if newly_created:
                collection_version = CollectionIndex.version
                self.write_version_to_yml(
                    self.album.configuration().get_catalog_collection_meta_path(), "my-collection", collection_version
                )
            else:
                raise RuntimeError(
                    "Album collection database file found, but no meta file specifying the database version."
                )
        if self.catalog_collection is not None:
            self.catalog_collection.close()
        self.catalog_collection = CollectionIndex(name=DefaultValues.catalog_collection_name.value,
                                                  path=self.album.configuration().get_catalog_collection_path())
        self.album.migration_manager().migrate_collection_index(
            self.catalog_collection,
            initial_version=collection_version
        )
        if newly_created:
            self.catalog_handler.add_initial_catalogs()
            self.catalog_handler.update_any()
            self.catalog_handler.update_collection()

    def catalogs(self) -> ICatalogHandler:
        return self.catalog_handler

    def solutions(self) -> ISolutionHandler:
        return self.solution_handler

    def add_solution_to_local_catalog(self, active_solution: ISolution, path):
        self.solution_handler.add_or_replace(self.catalog_handler.get_local_catalog(), active_solution, path)

    def get_index_as_dict(self):
        catalogs = self.catalog_collection.get_all_catalogs()
        for catalog in catalogs:
            solutions = []
            for solution in self.catalog_collection.get_solutions_by_catalog(catalog["catalog_id"]):
                solutions.append({
                    'setup': solution.setup(),
                    'internal': solution.internal()
                })
            catalog['solutions'] = solutions
        return {
            'catalogs': catalogs
        }

    def resolve_require_installation(self, resolve_solution) -> IResolveResult:
        resolve_result = self._resolve(resolve_solution)

        if not resolve_result.collection_entry():
            raise LookupError("Solution not found!")

        if not resolve_result.collection_entry().internal()["installed"]:
            raise ValueError("Solution seems not to be installed! Please install solution first!")

        return resolve_result

    def resolve_require_installation_and_load(self, resolve_solution) -> IResolveResult:
        resolve_result = self.resolve_require_installation(resolve_solution)

        loaded_solution = self.album.state_manager().load(resolve_result.path())
        self.solutions().set_cache_paths(loaded_solution, resolve_result.catalog())

        resolve_result.set_loaded_solution(loaded_solution)

        return resolve_result

    def resolve_download_and_load(self, resolve_solution) -> IResolveResult:
        resolve_result = self._resolve(resolve_solution)
        self.retrieve_and_load_resolve_result(resolve_result)
        self.solutions().set_cache_paths(resolve_result.loaded_solution(), resolve_result.catalog())

        return resolve_result

    def resolve_download_and_load_catalog_coordinates(self, catalog: ICatalog,
                                                      coordinates: ICoordinates) -> IResolveResult:
        collection_entry = self._search_in_specific_catalog(catalog.catalog_id(), coordinates)
        solution_path = self.solutions().get_solution_file(catalog, coordinates)

        resolve_result = ResolveResult(
            path=solution_path, catalog=catalog, collection_entry=collection_entry, coordinates=coordinates
        )
        self.retrieve_and_load_resolve_result(resolve_result)

        self.solutions().set_cache_paths(resolve_result.loaded_solution(), resolve_result.catalog())

        return resolve_result

    def resolve_download_and_load_coordinates(self, coordinates: ICoordinates) -> IResolveResult:
        collection_entry = self._search_by_coordinates(coordinates)
        catalog = self.catalogs().get_by_id(collection_entry.internal()["catalog_id"])

        solution_path = self.solutions().get_solution_file(catalog, coordinates)
        resolve_result = ResolveResult(
            path=solution_path, catalog=catalog, collection_entry=collection_entry, coordinates=coordinates
        )
        self.retrieve_and_load_resolve_result(resolve_result)

        self.solutions().set_cache_paths(resolve_result.loaded_solution(), resolve_result.catalog())

        return resolve_result

    def resolve_download(self, resolve_solution) -> IResolveResult:
        resolve_result = self._resolve(resolve_solution)

        if not Path(resolve_result.path()).exists():
            self.solutions().retrieve_solution(resolve_result.catalog(), resolve_result.coordinates())

        return resolve_result

    def resolve_parent(self, parent_dict: dict) -> IResolveResult:
        # resolve the parent mentioned in the current solution to get its metadata
        resolve_parent_info = build_resolve_string(parent_dict)
        parent_resolve_result = self.resolve_require_installation(resolve_parent_info)

        # resolve parent of the parent
        parent = get_parent(parent_resolve_result.collection_entry())

        # case parent itself has no further parent
        if parent.internal()["collection_id"] == parent_resolve_result.collection_entry().internal()["collection_id"]:

            loaded_solution = self.album.state_manager().load(parent_resolve_result.path())
            self.solutions().set_cache_paths(loaded_solution, parent_resolve_result.catalog())

            parent_resolve_result.set_loaded_solution(loaded_solution)

        # case parent itself has another parent
        else:
            parent_catalog = self.catalogs().get_by_id(parent.internal()["catalog_id"])
            parent_coordinates = dict_to_coordinates(parent.setup())
            path = self.solutions().get_solution_file(parent_catalog, parent_coordinates)

            loaded_solution = self.album.state_manager().load(path)
            self.solutions().set_cache_paths(loaded_solution, parent_catalog)

            parent_resolve_result = ResolveResult(
                path=path,
                catalog=parent_catalog,
                collection_entry=parent,
                coordinates=parent_coordinates,
                loaded_solution=loaded_solution
            )

        return parent_resolve_result

    def _resolve(self, str_input) -> IResolveResult:
        # always first resolve outside any catalog, excluding a DOI which should be first resolved inside a catalog
        path = check_file_or_url(str_input, self.album.configuration().cache_path_tmp_user())

        doi = get_doi_from_input(str_input)
        if path:
            # will load the solution behind the path to get meta-information
            solution_entry = self._search_for_local_file(path)

            # a solution loaded this way will always end up in a local catalog
            catalog = self.catalog_handler.get_local_catalog()
        else:
            # search DOI first
            if doi:
                solution_entry = self._search_doi(doi["doi"])

                # either a doi is found in the collection or it will be downloaded and ends up in a local catalog
                if solution_entry:
                    catalog = self.catalog_handler.get_by_id(solution_entry.internal["catalog_id"])
                else:
                    # download DOI
                    path = check_doi(doi["doi"], self.album.configuration().cache_path_tmp_user())

                    catalog = self.catalog_handler.get_local_catalog()
            else:  # case no doi
                solution_entry = self._search(str_input)

                if not solution_entry:
                    raise LookupError("Solution cannot be resolved in any catalog!")

                catalog = self.catalog_handler.get_by_id(solution_entry.internal()["catalog_id"])

                path = self.solutions().get_solution_file(catalog, dict_to_coordinates(solution_entry.setup()))

        coordinates = None

        if solution_entry:
            coordinates = dict_to_coordinates(solution_entry.setup())

        resolve = ResolveResult(
            path=path, catalog=catalog, collection_entry=solution_entry, coordinates=coordinates
        )

        return resolve

    def _search_for_local_file(self, path) -> ICollectionIndex.ICollectionSolution:
        active_solution = self.album.state_manager().load(path)

        # check in collection
        solution_entry = self.catalog_collection.get_solution_by_catalog_grp_name_version(
            self.catalog_handler.get_local_catalog().catalog_id(),
            active_solution.coordinates()
        )

        return solution_entry

    def _search_doi(self, doi):
        solution_entry = self.catalog_collection.get_solution_by_doi(doi)

        return solution_entry

    def _search(self, str_input) -> ICollectionIndex.ICollectionSolution:
        """Searches ONLY in the catalog collection, given a string which is interpreted."""
        attrs = get_attributes_from_string(str_input)

        solution_entry = None
        if "doi" in attrs:  # case doi
            solution_entry = self._search_doi(attrs["doi"])
        else:
            coordinates = dict_to_coordinates(attrs)
            if "catalog" not in attrs:
                solution_entry = self._search_in_local_catalog(coordinates)  # resolve in local catalog first!

            if not solution_entry:
                if "catalog" in attrs:  # resolve in specific catalog
                    catalog_id = self.catalog_handler.get_by_name(attrs["catalog"]).catalog_id()
                    solution_entry = self._search_in_specific_catalog(catalog_id, coordinates)
                else:
                    solution_entries = self._search_in_catalogs(coordinates)  # resolve anywhere

                    if solution_entries and len(solution_entries) > 1:
                        module_logger().warning("Found several solutions... taking the first one! ")

                    if solution_entries:
                        solution_entry = solution_entries[0]

        return solution_entry

    def _search_by_coordinates(self, coordinates: ICoordinates) -> Optional[ICollectionIndex.ICollectionSolution]:
        solution_entry = self._search_in_local_catalog(coordinates)  # resolve in local catalog first!

        if not solution_entry:
            solution_entries = self._search_in_catalogs(coordinates)  # resolve anywhere

            if solution_entries and len(solution_entries) > 1:
                module_logger().warning("Found several solutions... taking the first one! ")

            if solution_entries:
                solution_entry = solution_entries[0]

        return solution_entry

    def _search_in_local_catalog(self, coordinates: ICoordinates) -> Optional[ICollectionIndex.ICollectionSolution]:
        """Searches in the local catalog only"""
        return self._search_in_specific_catalog(self.catalog_handler.get_local_catalog().catalog_id(), coordinates)

    def _search_in_specific_catalog(self, catalog_id, coordinates: ICoordinates) \
            -> Optional[ICollectionIndex.ICollectionSolution]:
        """Searches in a given catalog only"""
        return self.catalog_collection.get_solution_by_catalog_grp_name_version(catalog_id, coordinates)

    def _search_in_catalogs(self, coordinates: ICoordinates) -> List[ICollectionIndex.ICollectionSolution]:
        """Searches the whole collection giving coordinates"""
        solution_entries = self.catalog_collection.get_solutions_by_grp_name_version(coordinates)

        return solution_entries if solution_entries else None

    def retrieve_and_load_resolve_result(self, resolve_result: IResolveResult):
        if not Path(resolve_result.path()).exists():
            self.solutions().retrieve_solution(resolve_result.catalog(),
                                               dict_to_coordinates(resolve_result.collection_entry().setup()))
        resolve_result.set_loaded_solution(self.album.state_manager().load(resolve_result.path()))
        resolve_result.set_coordinates(resolve_result.loaded_solution().coordinates())

    @staticmethod
    def write_version_to_yml(path, name, version) -> None:
        write_dict_to_json(path, {
            "catalog_collection_name": name,
            "catalog_collection_version": version
        })
