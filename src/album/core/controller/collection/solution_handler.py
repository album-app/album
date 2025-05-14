import os
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Optional

from album.environments.utils.file_operations import copy, copy_folder
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.controller.controller import IAlbumController
from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_updates import ChangeType, ISolutionChange
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.model.link import Link
from album.core.utils.operations.file_operations import (
    construct_cache_link_target,
    force_remove,
)
from album.core.utils.operations.git_operations import (
    checkout_files,
    clone_repository_sparse,
)
from album.core.utils.operations.resolve_operations import (
    as_tag,
    dict_to_coordinates,
    get_zip_name,
)
from album.core.utils.operations.solution_operations import get_deploy_dict

module_logger = album_logging.get_active_logger


class SolutionHandler(ISolutionHandler):
    """Handles everything inside the Collection responsible for a solution entry.

    Is NOT responsible for resolving paths as this is part of a catalog.
    """

    def __init__(self, album: IAlbumController):
        self.album = album

    def add_or_replace(self, catalog: ICatalog, solution: ICollectionSolution) -> None:
        deploy_dict = get_deploy_dict(solution.loaded_solution())
        index = self._get_collection_index()
        if index is None:
            raise RuntimeError("Collection index not found!")

        index.add_or_replace_solution(
            catalog.catalog_id(), solution.coordinates(), deploy_dict
        )
        # get the installation location
        install_location = self.get_solution_package_path(
            catalog, dict_to_coordinates(deploy_dict)
        )

        if solution.is_single_file():
            if solution.path() is None:
                raise RuntimeError("Single file solution without path!")

            copy(
                solution.path(),
                install_location.joinpath(DefaultValues.solution_default_name.value),
            )
        else:
            _path = solution.path()

            if _path is None:
                raise RuntimeError("Solution without path!")

            copy_folder(Path(_path).parent, install_location, copy_root_folder=False)

    def add_to_cache_catalog(self, solution: ICollectionSolution) -> None:
        self.add_or_replace(self.album.catalogs().get_cache_catalog(), solution)

    def set_parent(
        self,
        parent_entry: ICollectionIndex.ICollectionSolution,
        child_entry: ICollectionIndex.ICollectionSolution,
    ) -> None:
        index = self._get_collection_index()
        if index is None:
            raise RuntimeError("Collection index not found!")

        index.insert_collection_collection(
            parent_entry.internal()["collection_id"],
            child_entry.internal()["collection_id"],
            parent_entry.internal()["catalog_id"],
            child_entry.internal()["catalog_id"],
        )

    def remove_parent(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        index = self._get_collection_index()
        if index is None:
            raise RuntimeError("Collection index not found!")

        entry = index.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates, close=False
        )
        if not entry:
            raise RuntimeError(
                "Solution %s not found in catalog %s!"
                % (str(coordinates), str(catalog.catalog_id()))
            )

        index.remove_parent(entry.internal()["collection_id"])

    def remove_solution(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        index = self._get_collection_index()
        if index is None:
            raise RuntimeError("Collection index not found!")

        index.remove_solution(catalog.catalog_id(), coordinates)

    def update_solution(
        self, catalog: ICatalog, coordinates: ICoordinates, attrs: dict
    ) -> None:
        index = self._get_collection_index()
        if index is None:
            raise RuntimeError("Collection index not found!")

        index.update_solution(
            catalog.catalog_id(),
            coordinates,
            attrs,
            CollectionIndex.get_collection_column_keys(),
        )

    def apply_change(
        self, catalog: ICatalog, change: ISolutionChange, override: bool
    ) -> None:
        cat_index = catalog.index()
        col_index = self._get_collection_index()
        sol_stat = change.solution_status()

        if cat_index is None:
            raise RuntimeError(
                "Catalog index not found for catalog %s!" % str(catalog.catalog_id())
            )

        # FIXME handle other tables (tags etc)
        if change.change_type() is ChangeType.ADDED:
            if col_index is None:
                raise RuntimeError("Collection index not found!")

            col_index.add_or_replace_solution(
                catalog.catalog_id(),
                change.coordinates(),
                cat_index.get_solution_by_coordinates(change.coordinates()),
            )

        elif change.change_type() is ChangeType.REMOVED:
            self.remove_solution(catalog, change.coordinates())

        elif change.change_type() is ChangeType.CHANGED:
            if not sol_stat:
                raise RuntimeError(
                    "Change type is CHANGED but no solution status found!"
                )

            if col_index is None:
                raise RuntimeError("Collection index not found!")

            # get install status before applying change
            installed = sol_stat["installed"]
            col_index.add_or_replace_solution(
                catalog.catalog_id(),
                change.coordinates(),
                cat_index.get_solution_by_coordinates(change.coordinates()),
            )
            if installed:
                # set old (install) status and parents again
                self._set_old_db_stat(catalog, change)

            if override and not catalog.is_cache() and installed:
                module_logger().warning(
                    'CAUTION: Solution "%s" seems to be installed.'
                    " The performed operation can leave a broken installation behind "
                    "if dependencies got changed! Consider reinstalling the solution!"
                    % str(change.coordinates())
                )
                self.retrieve_solution(catalog, change.coordinates())

    def _set_old_db_stat(self, catalog: ICatalog, change: ISolutionChange) -> None:
        sol_stat = change.solution_status()
        if sol_stat is None:
            raise RuntimeError("No solution status found in change!")

        index = self._get_collection_index()
        if index is None:
            raise RuntimeError("Collection index not found!")

        db_stat = self._get_db_status_dict(sol_stat)
        self.update_solution(catalog, change.coordinates(), db_stat)
        if sol_stat["parent"]:
            child_solution = index.get_solution_by_catalog_grp_name_version(
                catalog.catalog_id(), change.coordinates()
            )

            if not child_solution:
                raise RuntimeError(
                    "Solution %s not found in catalog %s!"
                    % (change.coordinates(), str(catalog.catalog_id()))
                )
            self.set_parent(sol_stat["parent"], child_solution)

    def set_installed(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        self.update_solution(
            catalog,
            coordinates,
            {
                "installed": 1,
                "installation_unfinished": 0,
                "install_date": datetime.now().isoformat(),
            },
        )

    def set_uninstalled(self, catalog: ICatalog, coordinates: ICoordinates) -> None:
        self.update_solution(
            catalog, coordinates, {"installed": 0, "installation_unfinished": 0}
        )

    def set_installation_unfinished(self, catalog: ICatalog, coordinates: ICoordinates):
        self.update_solution(
            catalog, coordinates, {"installed": 0, "installation_unfinished": 1}
        )

    def is_installed(self, catalog: ICatalog, coordinates: ICoordinates) -> bool:
        try:
            index = self._get_collection_index()
            if index is None:
                module_logger().warning("Collection index not found!")
                return False

            return index.is_installed(catalog.catalog_id(), coordinates)
        except LookupError:
            return False

    def get_solution_package_path(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> Link:
        base_link = catalog.path().joinpath(
            self.album.configuration().get_solution_path_suffix(coordinates)
        )
        link_target = construct_cache_link_target(
            self.album.configuration().lnk_path(),
            base_link,
            Path(DefaultValues.lnk_package_prefix.value),
        )
        return Link(link_target).set_link(link=base_link)

    def get_solution_installation_path(
        self, catalog: ICatalog, coordinates: ICoordinates
    ) -> Link:
        installation_path = self.album.configuration().installation_path()
        base_link = installation_path.joinpath(
            catalog.name(),
            coordinates.group(),
            coordinates.name(),
            coordinates.version(),
        )
        link_target = construct_cache_link_target(
            self.album.configuration().lnk_path(),
            base_link,
            Path(DefaultValues.lnk_solution_prefix.value),
        )
        return Link(link_target).set_link(link=base_link)

    def get_solution_file(self, catalog: ICatalog, coordinates: ICoordinates) -> Path:
        return self.get_solution_package_path(catalog, coordinates).joinpath(
            DefaultValues.solution_default_name.value
        )

    def get_solution_zip_suffix(self, coordinates: ICoordinates) -> Path:
        return Path("").joinpath(
            self.album.configuration().get_solution_path_suffix(coordinates),
            get_zip_name(coordinates),
        )

    def retrieve_solution(self, catalog: ICatalog, coordinates: ICoordinates) -> Path:
        if catalog.is_cache():  # no src to download form or src to copy from
            raise RuntimeError("Cannot download from a cache catalog!")
        else:  # src to download from
            solution_download_target = self.get_solution_package_path(
                catalog, coordinates
            )
            self._download_solution(
                catalog.src(), coordinates, solution_download_target
            )

        solution_path = solution_download_target.joinpath(
            DefaultValues.solution_default_name.value
        )

        return solution_path

    def _download_solution(self, src, coordinates: ICoordinates, target: Path) -> None:
        solution_pck = str(
            self.album.configuration().get_solution_path_suffix_unversioned(coordinates)
        )
        tag = as_tag(coordinates)
        with TemporaryDirectory(dir=self.album.configuration().tmp_path()) as tmp_dir:
            repo_dir = Path(tmp_dir).joinpath("repo")
            try:
                with clone_repository_sparse(src, tag, repo_dir) as repo:
                    checkout_files(repo, [solution_pck])
                tmp_solution = repo_dir.joinpath(solution_pck)
                if target.exists():
                    for f in os.listdir(str(target)):
                        force_remove(os.path.join(str(target), f))
                copy_folder(tmp_solution, target, copy_root_folder=False)
            finally:
                force_remove(repo_dir)

    def set_cache_paths(self, solution: ISolution, catalog: ICatalog) -> None:
        package_path = self.get_solution_package_path(catalog, solution.coordinates())
        solution_path = self.get_solution_installation_path(
            catalog, solution.coordinates()
        )
        solution.installation().set_package_path(package_path)
        solution.installation().set_installation_path(solution_path)

    def _get_collection_index(self) -> Optional[ICollectionIndex]:
        return self.album.collection_manager().get_collection_index()

    @staticmethod
    def _get_db_status_dict(internal_status: Dict[str, str]) -> Dict[str, str]:
        """Everything that should NOT change internally when an UPDATE change is performed on a solution."""
        r = {
            "installed": internal_status["installed"],
            "install_date": internal_status["install_date"],
            "last_execution": internal_status["last_execution"],
        }

        return r
