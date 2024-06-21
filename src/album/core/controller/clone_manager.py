from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import validators
from album.environments.utils.file_operations import copy, copy_folder
from album.environments.utils.url_operations import download_resource, is_downloadable
from album.runner.album_logging import get_active_logger
from git import Repo

from album.core.api.controller.clone_manager import ICloneManager
from album.core.api.controller.controller import IAlbumController
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import url_operations
from album.core.utils.operations.file_operations import (
    create_path_recursively,
    force_remove,
    get_dict_from_json,
    list_files_recursively,
    unzip_archive,
)
from album.core.utils.operations.git_operations import (
    add_files_commit_and_push,
    checkout_main,
    clone_repository,
    create_bare_repository,
)


class CloneManager(ICloneManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def clone(
        self,
        path: str,
        target_dir: str,
        name: str,
        git_email: Optional[str] = None,
        git_name: Optional[str] = None,
    ) -> None:
        if path.startswith("template:"):
            try:
                self._clone_catalog_template(
                    path[len("template:") :],  # noqa: E203
                    Path(target_dir),
                    name,
                    git_email,
                    git_name,
                )
            except (LookupError, ValueError):
                raise LookupError(
                    "Cannot resolve %s - make sure it's a valid name of a template located in %s!",
                    (path, DefaultValues.catalog_template_url.value),
                )
        else:
            target_path = Path(target_dir).joinpath(name)
            self._clone_solution(Path(path), target_path)

    def _clone_solution(self, path: Path, target_path: Path) -> None:
        resolve_result = self.album.collection_manager().resolve(str(path))

        if resolve_result.is_single_file():
            copy(
                resolve_result.path(),
                target_path.joinpath(DefaultValues.solution_default_name.value),
            )
        else:
            copy_folder(
                resolve_result.path().parent, target_path, copy_root_folder=False
            )

        get_active_logger().info(
            f"Copied solution {resolve_result.path()} to {target_path}!"
        )

    def _clone_catalog_template(
        self,
        template_name: str,
        target_path: Path,
        catalog_name: str,
        git_email: Optional[str] = None,
        git_name: Optional[str] = None,
    ) -> bool:
        template_url = "{c}/{n}/-/archive/main/{n}-main.zip".format(
            c=DefaultValues.catalog_template_url.value,
            n=template_name,
        )
        if is_downloadable(template_url):
            download_zip_target = (
                self.album.configuration()
                .cache_path_download()
                .joinpath(template_name + ".zip")
            )
            download_unzip_target = (
                self.album.configuration().cache_path_download().joinpath(template_name)
            )

            download_resource(template_url, download_zip_target)
            get_active_logger().debug(
                "Downloaded template from %s to %s!"
                % (template_url, download_zip_target)
            )

            unzip_archive(download_zip_target, download_unzip_target)
            download_unzip_target_subdir = download_unzip_target.joinpath(
                f"{template_name}-main"
            )

            self.setup_repository_from_template(
                target_path,
                download_unzip_target_subdir,
                catalog_name,
                git_email,
                git_name,
            )

            get_active_logger().info(
                'Initialized new catalog "%s" from template "%s" in %s!'
                % (catalog_name, template_name, target_path)
            )
            return True
        return False

    def setup_repository_from_template(
        self,
        target_path: Path,
        template_folder: Path,
        catalog_name: str,
        git_email: Optional[str] = None,
        git_name: Optional[str] = None,
    ):
        # test if target_path is a valid git repo path or a local path
        if validators.url(str(target_path)) or url_operations.is_git_ssh_address(
            str(target_path)
        ):
            with TemporaryDirectory(
                dir=self.album.configuration().tmp_path()
            ) as tmp_dir:
                tmp_clone_path = Path(tmp_dir).joinpath("clone")
                get_active_logger().info("Cloning target repository...")
                with clone_repository(target_path, tmp_clone_path) as repo:
                    self._copy_template_into_repository(
                        repo, template_folder, catalog_name, git_email, git_name
                    )
                force_remove(tmp_clone_path)
        else:
            create_path_recursively(target_path)
            create_bare_repository(target_path)
            with TemporaryDirectory(
                dir=self.album.configuration().tmp_path()
            ) as tmp_dir:
                tmp_clone_path = Path(tmp_dir).joinpath("clone")
                with clone_repository(target_path, tmp_clone_path) as repo:
                    self._copy_template_into_repository(
                        repo,
                        template_folder,
                        catalog_name,
                        email=DefaultValues.catalog_git_email.value,
                        username=DefaultValues.catalog_git_user.value,
                    )
                force_remove(tmp_clone_path)

    def _copy_template_into_repository(
        self,
        repo: Repo,
        template_folder: Path,
        catalog_name: str,
        email=None,
        username=None,
    ):
        head = checkout_main(repo)

        copy_folder(template_folder, repo.working_tree_dir, copy_root_folder=False)

        # create the metadata in repository clone
        catalog_type = self._get_catalog_type_from_template(template_folder)
        self.album.catalogs().create_new_metadata(
            repo.working_tree_dir, catalog_name, catalog_type
        )

        add_files_commit_and_push(
            head,
            list_files_recursively(repo.working_tree_dir),
            'Setting up "%s" catalog!' % catalog_name,
            push=True,
            force=False,
            email=email,
            username=username,
        )

    @staticmethod
    def _get_catalog_type_from_template(template_base_path: Path) -> str:
        template_metadata_path = CloneManager._get_metadata_path_from_template(
            template_base_path
        )

        if template_metadata_path.is_file():
            template_metadata = get_dict_from_json(template_metadata_path)
        else:
            raise FileNotFoundError(
                "Could not find file %s!" % str(template_metadata_path)
            )

        return template_metadata["type"]

    @staticmethod
    def _get_metadata_path_from_template(template_base_path: Path) -> Path:
        template_base_path = Path(template_base_path)
        template_metadata_path = template_base_path.joinpath(
            DefaultValues.catalog_index_metafile_json.value
        )

        return template_metadata_path
