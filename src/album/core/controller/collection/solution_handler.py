from datetime import datetime
from pathlib import Path

from album.core.api.album import IAlbum
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.model.catalog import ICatalog
from album.core.api.model.catalog_updates import ISolutionChange, ChangeType
from album.core.model.catalog import get_solution_src
from album.core.model.collection_index import CollectionIndex
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy_folder, copy, unzip_archive
from album.core.utils.operations.resolve_operations import dict_to_coordinates, get_zip_name
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.core.utils.operations.url_operations import download_resource
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


class SolutionHandler(ISolutionHandler):
    """Handles everything inside the Collection responsible for a solution entry.

    Is NOT responsible for resolving paths as this is part of a catalog.
    """

    def __init__(self, album: IAlbum):
        self.album = album

    def add_or_replace(self, catalog: ICatalog, active_solution: ISolution, path):
        deploy_dict = get_deploy_dict(active_solution)
        self.album.collection_manager().get_collection_index().add_or_replace_solution(
            catalog.catalog_id(),
            active_solution.coordinates(),
            deploy_dict
        )
        # get the install location
        install_location = self.get_solution_path(catalog, dict_to_coordinates(deploy_dict))

        copy_folder(path, install_location, copy_root_folder=False)

    def set_parent(self, catalog_parent: ICatalog, catalog_child: ICatalog, coordinates_parent: ICoordinates,
                   coordinates_child: ICoordinates):

        # retrieve parent entry
        parent_entry = self.album.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version(
            catalog_parent.catalog_id(), coordinates_parent, close=False
        )
        # retrieve child entry
        child_entry = self.album.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version(
            catalog_child.catalog_id(), coordinates_child, close=False
        )

        self.album.collection_manager().get_collection_index().insert_collection_collection(
            parent_entry.internal()["collection_id"],
            child_entry.internal()["collection_id"],
            catalog_parent.catalog_id(),
            catalog_child.catalog_id()
        )

    def remove_parent(self, catalog: ICatalog, coordinates: ICoordinates):
        entry = self.album.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates, close=False
        )
        self.album.collection_manager().get_collection_index().remove_parent(
            entry.internal()["collection_id"]
        )

    def remove_solution(self, catalog: ICatalog, coordinates: ICoordinates):
        self.album.collection_manager().get_collection_index().remove_solution(catalog.catalog_id(), coordinates)

    def update_solution(self, catalog: ICatalog, coordinates: ICoordinates, attrs: dict):
        self.album.collection_manager().get_collection_index().update_solution(
            catalog.catalog_id(),
            coordinates,
            attrs,
            CollectionIndex.get_collection_column_keys()
        )

    def apply_change(self, catalog: ICatalog, change: ISolutionChange):
        # FIXME handle other tables (tags etc)
        if change.change_type() is ChangeType.ADDED:
            self.album.collection_manager().get_collection_index().add_or_replace_solution(
                catalog.catalog_id(),
                change.coordinates(),
                catalog.index().get_solution_by_coordinates(change.coordinates())
            )

        elif change.change_type is ChangeType.REMOVED:
            self.remove_solution(catalog, change.coordinates())

        elif change.change_type is ChangeType.CHANGED:
            self.remove_solution(catalog, change.coordinates())
            self.album.collection_manager().get_collection_index().add_or_replace_solution(
                catalog.catalog_id(),
                change.coordinates(),
                catalog.index().get_solution_by_coordinates(change.coordinates())
            )

    def set_installed(self, catalog: ICatalog, coordinates: ICoordinates):
        self.update_solution(
            catalog,
            coordinates,
            {"installed": 1, "installation_unfinished": 0, "install_date": datetime.now().isoformat()}
        )

    def set_uninstalled(self, catalog: ICatalog, coordinates: ICoordinates):
        self.update_solution(catalog, coordinates, {"installed": 0, "installation_unfinished": 0})

    def set_installation_unfinished(self, catalog: ICatalog, coordinates: ICoordinates):
        self.update_solution(catalog, coordinates, {"installed": 0, "installation_unfinished": 1})

    def is_installed(self, catalog: ICatalog, coordinates: ICoordinates) -> bool:
        return self.album.collection_manager().get_collection_index().is_installed(catalog.catalog_id(), coordinates)

    def get_solution_path(self, catalog: ICatalog, coordinates: ICoordinates):
        return catalog.path().joinpath(self.album.configuration().get_solution_path_suffix(coordinates))

    def get_solution_file(self, catalog: ICatalog, coordinates: ICoordinates):
        p = self.get_solution_path(catalog, coordinates).joinpath(DefaultValues.solution_default_name.value)

        return p

    def get_solution_zip(self, catalog: ICatalog, coordinates: ICoordinates):
        return self.get_solution_path(catalog, coordinates).joinpath(get_zip_name(coordinates))

    def get_solution_zip_suffix(self, coordinates: ICoordinates):
        return Path("").joinpath(
            self.album.configuration().get_solution_path_suffix(coordinates),
            get_zip_name(coordinates)
        )

    def retrieve_solution(self, catalog: ICatalog, coordinates: ICoordinates):
        if catalog.is_cache():  # no src to download form or src to copy from
            raise RuntimeError("Cannot download from a cache catalog!")

        elif catalog.is_local():  # src to copy from
            src_path = Path(catalog.src()).joinpath(self.get_solution_zip_suffix(coordinates))
            solution_zip_file = self.get_solution_zip(catalog, coordinates)
            copy(src_path, solution_zip_file)

        else:  # src to download from
            url = get_solution_src(catalog.src(), coordinates, catalog.branch_name())
            solution_zip_file = self.get_solution_zip(catalog, coordinates)
            download_resource(url, solution_zip_file)

        solution_zip_path = unzip_archive(solution_zip_file)
        solution_path = solution_zip_path.joinpath(DefaultValues.solution_default_name.value)

        return solution_path

    def set_cache_paths(self, solution: ISolution, catalog: ICatalog):
        # Note: cache paths need the catalog the solution lives in - otherwise there might be problems with solutions
        # of different catalogs doing similar operations (e.g. downloads) as they might share the same cache path.
        path_suffix = Path("").joinpath(solution.coordinates().group(), solution.coordinates().name(),
                                        solution.coordinates().version())
        # FIXME this should be set differently, but not sure if we want to add public setters for these variables
        catalog_name = catalog.name()
        solution.installation().set_data_path(
            self.album.configuration().cache_path_download().joinpath(str(catalog_name), path_suffix))
        solution.installation().set_app_path(
            self.album.configuration().cache_path_app().joinpath(str(catalog_name), path_suffix))
        solution.installation().set_package_path(self.get_solution_path(catalog, solution.coordinates()))
        solution.installation().set_internal_cache_path(
            self.album.configuration().cache_path_tmp_internal().joinpath(str(catalog_name), path_suffix))
        solution.installation().set_user_cache_path(
            self.album.configuration().cache_path_tmp_user().joinpath(str(catalog_name), path_suffix))
