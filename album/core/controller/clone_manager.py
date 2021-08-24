from pathlib import Path

from album.core.concept.singleton import Singleton
from album.core.controller.catalog_handler import CatalogHandler
from album.core.controller.collection_manager import CollectionManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import url_operations, file_operations
from album_runner import logging

module_logger = logging.get_active_logger


class CloneManager(metaclass=Singleton):
    """Class handling the creation of new catalogs and solutions.
    """

    def __init__(self):
        self.collection_manager = CollectionManager()
        pass

    def clone(self, path, target_dir, name):
        """Function corresponding to the `clone` subcommand of `album`."""
        target_path = Path(target_dir).joinpath(name)
        try:
            self._try_cloning_solution(path, target_path)
        except (LookupError, ValueError):
            if not self._try_cloning_catalog_template(path, target_path, name):
                raise LookupError("Cannot resolve %s - make sure it's a valid path to a solution or the name of a "
                                  "template located in %s!", (path, DefaultValues.catalog_template_url.value))

    def _try_cloning_solution(self, path, target_path):
        resolve_result = self.collection_manager.resolve_download_and_load(path)
        target_path_solution = target_path.joinpath(DefaultValues.solution_default_name.value)
        file_operations.copy(resolve_result.path, target_path_solution)
        module_logger().info('Copied solution %s to %s!' % (resolve_result.path, target_path_solution))

    @staticmethod
    def _try_cloning_catalog_template(template_name, target_path, name):
        template_url = f"{DefaultValues.catalog_template_url.value}/{template_name}/-/archive/main/{template_name}-main.zip"
        if url_operations.is_downloadable(template_url):
            target_path.mkdir(parents=True)
            download_zip_target = CollectionManager().configuration.cache_path_download.joinpath(template_name + ".zip")
            download_unzip_target = CollectionManager().configuration.cache_path_download.joinpath(template_name)
            url_operations.download_resource(template_url, download_zip_target)
            file_operations.unzip_archive(download_zip_target, download_unzip_target)
            download_unzip_target_subdir = download_unzip_target.joinpath(f"{template_name}-main")
            file_operations.copy_folder(download_unzip_target_subdir, target_path, copy_root_folder=False)
            CatalogHandler.create_new_catalog(target_path, name)
            module_logger().info('Downloaded template from %s to %s!' % (template_url, target_path))
            return True
        return False


