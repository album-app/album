import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates

from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.collection.collection_manager import ICollectionManager
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.controller.controller import IAlbumController
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.collection.solution_handler import SolutionHandler
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.model.mmversion import MMVersion
from album.core.model.resolve_result import ResolveResult
from album.core.utils.operations.file_operations import write_dict_to_json
from album.core.utils.operations.resolve_operations import (
    check_doi,
    check_file_or_url,
    dict_to_coordinates,
    get_attributes_from_string,
    get_doi_from_input,
)

module_logger = album_logging.get_active_logger


class CollectionManager(ICollectionManager):
    def __init__(self, album: IAlbumController):
        self.album = album
        self.solution_handler = SolutionHandler(self.album)
        self.catalog_handler = CatalogHandler(self.album)
        self.catalog_collection: Optional[ICollectionIndex] = None
        self.collection_loaded = False

    def __del__(self):
        self.close()

    def close(self) -> None:
        if self.solution_handler is not None:
            del self.solution_handler
            self.solution_handler = SolutionHandler(self.album)
        if self.catalog_handler is not None:
            del self.catalog_handler
            self.catalog_handler = CatalogHandler(self.album)
        if self.catalog_collection is not None:
            self.catalog_collection.close()
            self.catalog_collection = None
        self.collection_loaded = False

    def get_collection_index(self) -> ICollectionIndex:
        if self.catalog_collection is None:
            raise LookupError("No collection loaded! Aborting...")
        return self.catalog_collection

    def load_or_create(self) -> None:
        if self.collection_loaded:
            module_logger().warning(
                "CollectionManager().load_or_create_collection() should only be called once."
            )
            return
        self.collection_loaded = True
        collection_meta = self.album.configuration().get_catalog_collection_meta_dict()
        newly_created = (
            not self.album.configuration().get_catalog_collection_path().exists()
        )
        if collection_meta:
            collection_version = collection_meta["catalog_collection_version"]
        else:
            if newly_created:
                collection_version = DefaultValues.catalog_collection_db_version.value
                self.write_version_to_json(
                    self.album.configuration().get_catalog_collection_meta_path(),
                    "my-collection",
                    collection_version,
                )
            else:
                # TODO: legacy code (if block), remove with first stable version of album
                # needed for backwards compatibility with old album collection versions
                if (
                    Path(self.album.configuration().get_catalog_collection_meta_path())
                    .parent.parent.joinpath(
                        DefaultValues.catalog_collection_json_name.value
                    )
                    .exists()
                ):
                    shutil.move(
                        str(
                            Path(
                                self.album.configuration()
                                .get_catalog_collection_meta_path()
                                .parent.parent.joinpath(
                                    DefaultValues.catalog_collection_json_name.value
                                )
                            )
                        ),
                        Path(
                            self.album.configuration().get_catalog_collection_meta_path()
                        ),
                    )
                    collection_meta = (
                        self.album.configuration().get_catalog_collection_meta_dict()
                    )
                    if collection_meta is None:
                        raise RuntimeError(
                            "Album collection database file found, but no meta file specifying the database version."
                        )

                    collection_version = collection_meta["catalog_collection_version"]
                else:
                    raise RuntimeError(
                        "Album collection database file found, but no meta file specifying the database version."
                    )
        if self.catalog_collection is not None:
            self.catalog_collection.close()
        self.catalog_collection = CollectionIndex(
            name=DefaultValues.catalog_collection_name.value,
            path=self.album.configuration().get_catalog_collection_path(),
        )
        self.album.migration_manager().migrate_collection_index(
            self.catalog_collection,
            initial_version=MMVersion.from_string(collection_version),
        )
        if newly_created:
            self.catalog_handler.add_initial_catalogs()

    def catalogs(self) -> ICatalogHandler:
        return self.catalog_handler

    def solutions(self) -> ISolutionHandler:
        return self.solution_handler

    def get_index_as_dict(self) -> Dict[str, Any]:
        if self.catalog_collection is None:
            return {}

        catalogs = self.catalog_collection.get_all_catalogs()
        for catalog in catalogs:
            solutions = []
            for solution in self.catalog_collection.get_solutions_by_catalog(
                catalog["catalog_id"]
            ):
                solutions.append(
                    {"setup": solution.setup(), "internal": solution.internal()}
                )
            catalog["solutions"] = solutions
        return {
            "base": str(self.album.configuration().base_cache_path()),
            "catalogs": catalogs,
        }

    def resolve_installed(self, resolve_solution: str) -> ICollectionSolution:
        resolve_result = self._resolve(resolve_solution)

        db_entry = resolve_result.database_entry()

        if not db_entry:
            raise LookupError("Solution not found in database!")

        if not db_entry.internal()["installed"]:
            raise ValueError(
                "Solution seems not to be installed! Please install solution first!"
            )

        return resolve_result

    def resolve_installed_and_load(self, resolve_solution: str) -> ICollectionSolution:
        resolve_result = self.resolve_installed(resolve_solution)

        loaded_solution = self.album.state_manager().load(resolve_result.path())
        self.solution_handler.set_cache_paths(loaded_solution, resolve_result.catalog())

        resolve_result.set_loaded_solution(loaded_solution)

        return resolve_result

    def resolve_and_load(self, resolve_solution: str) -> ICollectionSolution:
        resolve_result = self._resolve(resolve_solution)
        self.retrieve_and_load_resolve_result(resolve_result)
        self.solution_handler.set_cache_paths(
            resolve_result.loaded_solution(), resolve_result.catalog()
        )

        return resolve_result

    def resolve_and_load_catalog_coordinates(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> ICollectionSolution:
        collection_entry = self._search_in_specific_catalog(
            catalog.catalog_id(), coordinates
        )
        if not collection_entry:
            raise LookupError(
                "Cannot find solution %s in catalog %s! Aborting..."
                % (coordinates, catalog.name())
            )

        solution_path = self.solution_handler.get_solution_file(catalog, coordinates)

        resolve_result = ResolveResult(
            path=solution_path,
            catalog=catalog,
            collection_entry=collection_entry,
            coordinates=coordinates,
        )
        self.retrieve_and_load_resolve_result(resolve_result)

        self.solution_handler.set_cache_paths(
            resolve_result.loaded_solution(), resolve_result.catalog()
        )

        return resolve_result

    def resolve_and_load_coordinates(
        self, coordinates: ICoordinates
    ) -> ICollectionSolution:
        collection_entry = self._search_by_coordinates(coordinates)
        if collection_entry is None:
            raise LookupError("Cannot find solution %s! Aborting..." % coordinates)

        catalog = self.album.catalogs().get_by_id(
            collection_entry.internal()["catalog_id"]
        )

        solution_path = self.solution_handler.get_solution_file(catalog, coordinates)
        resolve_result = ResolveResult(
            path=solution_path,
            catalog=catalog,
            collection_entry=collection_entry,
            coordinates=coordinates,
        )
        self.retrieve_and_load_resolve_result(resolve_result)

        self.solution_handler.set_cache_paths(
            resolve_result.loaded_solution(), resolve_result.catalog()
        )

        return resolve_result

    def resolve(self, str_input: str) -> ICollectionSolution:
        resolve_result = self._resolve(str_input)

        if not Path(resolve_result.path()).exists():
            self.solution_handler.retrieve_solution(
                resolve_result.catalog(), resolve_result.coordinates()
            )

        return resolve_result

    def _resolve(self, str_input: str) -> ICollectionSolution:
        str_input = str(str_input)

        # always first resolve outside any catalog, excluding a DOI which should be first resolved inside a catalog
        path = check_file_or_url(
            str_input, self.album.configuration().cache_path_download()
        )

        single_file = False

        doi = get_doi_from_input(str_input)
        if path:
            if not path.exists():
                raise FileNotFoundError(path)
            single_file = path.is_file() and not path.is_dir()

            if not single_file:
                path = path.joinpath(DefaultValues.solution_default_name.value)

            # will load the solution behind the path to get meta-information
            solution_entry = self._search_for_local_file(path)

            # a solution loaded this way will always end up in a local catalog
            catalog = self.album.catalogs().get_cache_catalog()
        else:
            # search DOI first
            if doi:
                solution_entry = self._search_doi(doi["doi"])

                # either a doi is found in the collection or it will be downloaded and ends up in a local catalog
                if solution_entry:
                    catalog = self.album.catalogs().get_by_id(
                        solution_entry.internal()["catalog_id"]
                    )
                    path = self.solution_handler.get_solution_file(
                        catalog, dict_to_coordinates(solution_entry.setup())
                    )
                else:
                    # download DOI
                    path = check_doi(doi["doi"], self.album.configuration().tmp_path())
                    catalog = self.album.catalogs().get_cache_catalog()
            else:  # case no doi
                solution_entry = self._search(str_input)

                if not solution_entry:
                    raise LookupError(
                        "Cannot find solution %s! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> "
                        "or <group>:<name>:<version> or <catalog>:<group>:<name>:<version> "
                        "or point to a valid file or folder! Aborting..." % str_input
                    )

                catalog = self.album.catalogs().get_by_id(
                    solution_entry.internal()["catalog_id"]
                )
                path = self.solution_handler.get_solution_file(
                    catalog,
                    dict_to_coordinates(
                        solution_entry.setup()
                    ),  # this path must not exist yet
                )

        coordinates = None

        if solution_entry:
            coordinates = dict_to_coordinates(solution_entry.setup())

        if not path:  # internal error
            raise LookupError(
                "Cannot find solution %s! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> "
                "or <group>:<name>:<version> or <catalog>:<group>:<name>:<version> "
                "or point to a valid file or folder! Aborting..." % str_input
            )

        resolve = ResolveResult(
            path=path,  # never None
            catalog=catalog,  # always set
            collection_entry=solution_entry,  # only None if resolved to a path or DOI
            coordinates=coordinates,  # only None if resolved to a path or DOI
            single_file_solution=single_file,  # only True if resolved to a path
        )

        return resolve

    def _search_for_local_file(
        self, path: Path
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        active_solution = self.album.state_manager().load(path)

        if self.catalog_collection is None:
            raise LookupError("No collection loaded! Aborting...")

        # check in collection
        solution_entry = (
            self.catalog_collection.get_solution_by_catalog_grp_name_version(
                self.album.catalogs().get_cache_catalog().catalog_id(),
                active_solution.coordinates(),
            )
        )

        return solution_entry

    def _search_doi(self, doi: str):
        if self.catalog_collection is None:
            raise LookupError("No collection loaded! Aborting...")

        solution_entry = self.catalog_collection.get_solution_by_doi(doi)

        return solution_entry

    def _search(self, str_input: str) -> Optional[ICollectionIndex.ICollectionSolution]:
        try:
            attrs = get_attributes_from_string(str_input)
        except ValueError:
            return self._guess(str_input)

        solution_entry = None
        if "doi" in attrs:  # case doi
            solution_entry = self._search_doi(attrs["doi"])
        else:
            coordinates = dict_to_coordinates(attrs)
            if "catalog" not in attrs:
                solution_entry = self._search_in_local_catalog(
                    coordinates
                )  # resolve in local catalog first!

            if not solution_entry:
                if "catalog" in attrs:  # resolve in specific catalog
                    catalog_id = (
                        self.album.catalogs().get_by_name(attrs["catalog"]).catalog_id()
                    )
                    solution_entry = self._search_in_specific_catalog(
                        catalog_id, coordinates
                    )
                else:
                    solution_entries = self._search_in_catalogs(
                        coordinates
                    )  # resolve anywhere

                    if solution_entries and len(solution_entries) > 1:
                        module_logger().warning(
                            "Found several solutions... taking the first one! "
                        )

                    if solution_entries:
                        solution_entry = solution_entries[0]
        return solution_entry

    def _search_by_coordinates(
        self, coordinates: ICoordinates
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        solution_entry = self._search_in_local_catalog(
            coordinates
        )  # resolve in local catalog first!

        if not solution_entry:
            solution_entries = self._search_in_catalogs(coordinates)  # resolve anywhere

            if solution_entries and len(solution_entries) > 1:
                module_logger().warning(
                    "Found several solutions... taking the first one! "
                )

            if solution_entries:
                solution_entry = solution_entries[0]

        return solution_entry

    def _search_in_local_catalog(
        self, coordinates: ICoordinates
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        return self._search_in_specific_catalog(
            self.album.catalogs().get_cache_catalog().catalog_id(), coordinates
        )

    def _search_in_specific_catalog(
        self, catalog_id: int, coordinates: ICoordinates
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        if self.catalog_collection is None:
            raise LookupError("No collection loaded! Aborting...")

        return self.catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog_id, coordinates
        )

    def _search_in_catalogs(
        self, coordinates: ICoordinates
    ) -> List[ICollectionIndex.ICollectionSolution]:
        if self.catalog_collection is None:
            raise LookupError("No collection loaded! Aborting...")

        solution_entries = self.catalog_collection.get_solutions_by_grp_name_version(
            coordinates
        )

        return solution_entries

    def retrieve_and_load_resolve_result(
        self, resolve_result: ICollectionSolution
    ) -> None:
        db_entry = resolve_result.database_entry()

        if not resolve_result.path() or not resolve_result.path().exists():
            if not db_entry:
                raise LookupError("Solution not found!")

            self.solution_handler.retrieve_solution(
                resolve_result.catalog(),
                dict_to_coordinates(db_entry.setup()),
            )
        resolve_result.set_loaded_solution(
            self.album.state_manager().load(resolve_result.path())
        )
        resolve_result.set_coordinates(resolve_result.loaded_solution().coordinates())

    @staticmethod
    def write_version_to_json(path: Path, name: str, version: str) -> None:
        write_dict_to_json(
            path,
            {"catalog_collection_name": name, "catalog_collection_version": version},
        )

    def _guess(self, str_input: str) -> Optional[ICollectionIndex.ICollectionSolution]:
        if self.catalog_collection is None:
            raise LookupError("No collection loaded! Aborting...")

        input_parts = str_input.split(":")
        call_not_reproducible = (
            "This call is not fully reproducible. Resolving to this solution: %s"
        )

        if len(input_parts) == 1:
            solutions = self.catalog_collection.get_solutions_by_name(input_parts[0])
            if len(solutions) == 1:
                module_logger().warn(
                    call_not_reproducible % dict_to_coordinates(solutions[0].setup())
                )
                return solutions[0]
            if len(solutions) > 1:
                return self._handle_multiple_solution_matches(solutions)
            else:
                return None
        if len(input_parts) == 2:
            solutions = self.catalog_collection.get_solutions_by_name_version(
                input_parts[0], input_parts[1]
            )
            if len(solutions) == 1:
                module_logger().warn(
                    call_not_reproducible % dict_to_coordinates(solutions[0].setup())
                )
                return solutions[0]
            if len(solutions) > 1:
                return self._handle_multiple_solution_matches(solutions)
            if len(solutions) == 0:
                solutions = self.catalog_collection.get_solutions_by_grp_name(
                    input_parts[0], input_parts[1]
                )
                if len(solutions) == 1:
                    module_logger().warn(
                        call_not_reproducible
                        % dict_to_coordinates(solutions[0].setup())
                    )
                    return solutions[0]
                if len(solutions) > 1:
                    return self._handle_multiple_solution_matches(solutions)
        return None

    def _handle_multiple_solution_matches(
        self, solutions: List[ICollectionIndex.ICollectionSolution]
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        call_not_reproducible = "Resolving ambiguous input to %s"
        cache_id = self.catalogs().get_cache_catalog().catalog_id()
        cache_matches = [
            solution
            for solution in solutions
            if solution.internal()["catalog_id"] == cache_id
        ]
        non_cache_matches = [
            solution
            for solution in solutions
            if solution.internal()["catalog_id"] != cache_id
        ]
        if len(cache_matches) == 1:
            module_logger().warn(
                call_not_reproducible % dict_to_coordinates(cache_matches[0].setup())
            )
            return cache_matches[0]
        elif len(cache_matches) > 1:
            latest_installed_solution = self._get_latest_installed_solution(
                cache_matches
            )
            if latest_installed_solution:
                module_logger().warn(
                    call_not_reproducible
                    % dict_to_coordinates(latest_installed_solution.setup())
                )
            return latest_installed_solution
        elif len(non_cache_matches) > 0:
            latest_installed_solution = self._get_latest_installed_solution(
                non_cache_matches
            )
            if latest_installed_solution:
                module_logger().warn(
                    call_not_reproducible
                    % dict_to_coordinates(latest_installed_solution.setup())
                )
                return latest_installed_solution
            else:
                latest_solution = self._get_latest_solution(non_cache_matches)
                if latest_solution:
                    module_logger().warn(
                        call_not_reproducible
                        % dict_to_coordinates(latest_solution.setup())
                    )
                    return latest_solution
        return None

    def _solutions_as_list(
        self, solutions: List[ICollectionIndex.ICollectionSolution]
    ) -> str:
        solutions_str = ""
        for solution in solutions:
            catalog_name = (
                self.catalogs().get_by_id(solution.internal()["catalog_id"]).name()
            )
            solutions_str += "- {n}:{c}\n".format(
                n=catalog_name,
                c=dict_to_coordinates(solution.setup()),
            )
        return solutions_str

    @staticmethod
    def _get_latest_installed_solution(
        solutions: List[ICollectionIndex.ICollectionSolution],
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        installed_solutions = [
            solution for solution in solutions if solution.internal()["installed"] == 1
        ]
        return CollectionManager._get_latest_solution(installed_solutions)

    @staticmethod
    def _get_latest_solution(
        solutions: List[ICollectionIndex.ICollectionSolution],
    ) -> Optional[ICollectionIndex.ICollectionSolution]:
        latest_solution = solutions[0]
        for solution in solutions:
            if MMVersion.from_string(
                solution.setup()["version"]
            ) > MMVersion.from_string(latest_solution.setup()["version"]):
                latest_solution = solution
        return latest_solution
