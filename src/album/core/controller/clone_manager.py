from pathlib import Path

from album.core.api.album import IAlbum
from album.core.api.controller.clone_manager import ICloneManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import url_operations, file_operations
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class CloneManager(ICloneManager):
    def __init__(self, album: IAlbum):
        self.collection_manager = album.collection_manager()
        self.configuration = album.configuration()

    def clone(self, path: str, target_dir: str, name: str) -> None:
        target_path = Path(target_dir).joinpath(name)
        if path.startswith("template:"):
            try:
                self._clone_catalog_template(path[len("template:"):], target_path, name)
            except (LookupError, ValueError):
                raise LookupError("Cannot resolve %s - make sure it's a valid name of a template located in %s!",
                                  (path, DefaultValues.catalog_template_url.value))
        else:
            self._clone_solution(path, target_path)

    def _clone_solution(self, path, target_path):
        """Copies a solution (by resolving and downloading) to a given target path."""
        resolve_result = self.collection_manager.resolve_download(path)
        target_path_solution = target_path.joinpath(DefaultValues.solution_default_name.value)
        file_operations.copy(resolve_result.path(), target_path_solution)
        module_logger().info('Copied solution %s to %s!' % (resolve_result.path(), target_path_solution))

    def _clone_catalog_template(self, template_name, target_path, name):
        """Clones a template by looking up the template name in the template catalog"""
        template_url = "%s/%s/-/archive/main/%s-main.zip" % (
            DefaultValues.catalog_template_url.value, template_name, template_name
        )
        if url_operations.is_downloadable(template_url):
            target_path.mkdir(parents=True)
            download_zip_target = self.configuration.cache_path_download().joinpath(template_name + ".zip")
            download_unzip_target = self.configuration.cache_path_download().joinpath(template_name)
            url_operations.download_resource(template_url, download_zip_target)
            file_operations.unzip_archive(download_zip_target, download_unzip_target)
            download_unzip_target_subdir = download_unzip_target.joinpath(f"{template_name}-main")
            file_operations.copy_folder(download_unzip_target_subdir, target_path, copy_root_folder=False)
            self.collection_manager.catalogs().create_new(target_path, name)
            module_logger().info('Downloaded template from %s to %s!' % (template_url, target_path))
            return True
        return False
