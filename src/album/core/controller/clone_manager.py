from pathlib import Path
from tempfile import TemporaryDirectory

from album.core.api.controller.clone_manager import ICloneManager
from album.core.api.controller.controller import IAlbumController
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import url_operations, file_operations
from album.core.utils.operations.file_operations import create_path_recursively, get_dict_from_json, \
    list_files_recursively, force_remove
from album.core.utils.operations.git_operations import create_bare_repository, clone_repository, \
    add_files_commit_and_push, checkout_main
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class CloneManager(ICloneManager):
    def __init__(self, album: IAlbumController):
        self.album = album

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
        resolve_result = self.album.collection_manager().resolve(path)

        target_path_solution = target_path.joinpath(DefaultValues.solution_default_name.value)
        file_operations.copy(resolve_result.path(), target_path_solution)

        module_logger().info('Copied solution %s to %s!' % (resolve_result.path(), target_path_solution))

    def _clone_catalog_template(self, template_name, target_path, catalog_name):
        """Clones a template by looking up the template name in the template catalog"""
        template_url = "%s/%s/-/archive/main/%s-main.zip" % (
            DefaultValues.catalog_template_url.value, template_name, template_name
        )
        if url_operations.is_downloadable(template_url):
            create_path_recursively(target_path)

            download_zip_target = self.album.configuration().cache_path_download().joinpath(template_name + ".zip")
            download_unzip_target = self.album.configuration().cache_path_download().joinpath(template_name)

            url_operations.download_resource(template_url, download_zip_target)
            module_logger().debug('Downloaded template from %s to %s!' % (template_url, download_zip_target))

            file_operations.unzip_archive(download_zip_target, download_unzip_target)
            download_unzip_target_subdir = download_unzip_target.joinpath(f"{template_name}-main")

            self.setup_repository_from_template(target_path, download_unzip_target_subdir, catalog_name)

            module_logger().info("Initialized new catalog \"%s\" from template \"%s\" in %s!" % (
                catalog_name, template_name, target_path
            ))
            return True
        return False

    def setup_repository_from_template(self, target_path, template_folder, catalog_name):
        create_bare_repository(target_path)

        # initial push to the bare_repository
        with TemporaryDirectory(dir=self.album.configuration().cache_path_tmp_internal()) as tmp_dir:
            tmp_clone_path = Path(tmp_dir).joinpath("clone")
            with clone_repository(target_path, tmp_clone_path) as repo:
                head = checkout_main(repo)

                file_operations.copy_folder(
                    template_folder, repo.working_tree_dir, copy_root_folder=False
                )

                # create the metadata in repository clone
                catalog_type = self._get_catalog_type_from_template(template_folder)
                self.album.catalogs().create_new_metadata(repo.working_tree_dir, catalog_name, catalog_type)

                add_files_commit_and_push(
                    head,
                    list_files_recursively(repo.working_tree_dir),
                    "Setting up \"%s\" catalog!" % catalog_name,
                    push=True,
                    force=False,
                    email=DefaultValues.catalog_git_email.value,

                    username=DefaultValues.catalog_git_user.value
                )
            force_remove(tmp_clone_path)

    @staticmethod
    def _get_catalog_type_from_template(template_base_path):
        template_metadata_path = CloneManager._get_metadata_path_from_template(template_base_path)

        if template_metadata_path.is_file():
            template_metadata = get_dict_from_json(template_metadata_path)
        else:
            raise FileNotFoundError("Could not find file %s!" % str(template_metadata_path))

        return template_metadata["type"]

    @staticmethod
    def _get_metadata_path_from_template(template_base_path):
        template_base_path = Path(template_base_path)
        template_metadata_path = template_base_path.joinpath(DefaultValues.catalog_index_metafile_json.value)

        return template_metadata_path
