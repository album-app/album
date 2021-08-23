from pathlib import Path

from album.core.concept.singleton import Singleton
from album.core.controller.collection_manager import CollectionManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import git_operations, url_operations, file_operations
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

        # check if path is a solution / can be resolved
        try:
            resolve_result = self.collection_manager.resolve_download_and_load(path)
            target_path_solution = target_path.joinpath(DefaultValues.solution_default_name.value)
            file_operations.copy(resolve_result.path, target_path_solution)
            module_logger().info('Copied solution %s to %s!' % (resolve_result.path, target_path_solution))
        except (LookupError, ValueError):
            # check if template name is given
            template_url = f"{DefaultValues.catalog_template_url.value}/{path}/-/archive/main/{path}-main.zip"
            if url_operations.is_downloadable(template_url):
                target_path.mkdir(parents=True)
                download_zip_target = CollectionManager().configuration.cache_path_download.joinpath(path+".zip")
                download_unzip_target = CollectionManager().configuration.cache_path_download.joinpath(path)
                url_operations.download_resource(template_url, download_zip_target)
                file_operations.unzip_archive(download_zip_target, download_unzip_target)
                download_unzip_target_subdir = download_unzip_target.joinpath(f"{path}-main")
                file_operations.copy_folder(download_unzip_target_subdir, target_path, copy_root_folder=False)
                module_logger().info('Downloaded template from %s to %s!' % (template_url, target_path))
                pass
            else:
                raise LookupError("Cannot resolve %s - make sure it's a valid path to a solution or the name of a "
                                  "template located in %s!", (path, DefaultValues.catalog_template_url.value))


