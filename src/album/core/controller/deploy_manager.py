from datetime import datetime
from pathlib import Path
from typing import List, Optional

from album.environments.utils.file_operations import force_remove
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution
from git import Repo

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.deploy_manager import IDeployManager
from album.core.api.model.catalog import ICatalog
from album.core.model.default_values import DefaultValues
from album.core.utils.export.changelog import process_changelog_file
from album.core.utils.operations.file_operations import folder_empty
from album.core.utils.operations.git_operations import (
    add_files_commit_and_push,
    add_tag,
    checkout_main,
    clean_repository,
    create_new_head,
    get_tags,
    remove_files,
    remove_tag,
    retrieve_default_mr_push_options,
    revert,
)
from album.core.utils.operations.resolve_operations import (
    as_tag,
    as_tag_unversioned,
    dict_to_coordinates,
    get_attributes_from_string,
)

module_logger = album_logging.get_active_logger


class DeployManager(IDeployManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def deploy(
        self,
        deploy_path: str,
        catalog_name: str,
        dry_run: bool,
        push_options: Optional[List[str]] = None,
        git_email: str = "",
        git_name: str = "",
        force_deploy: bool = False,
        changelog: str = "",
        no_conda_lock: bool = False,
    ):
        _push_options = push_options if push_options is not None else []
        if dry_run:
            module_logger().info(
                f"Pretending to deploy {deploy_path} to {catalog_name}..."
            )
        else:
            module_logger().info(f"Deploying {deploy_path} to {catalog_name}...")

        _deploy_path = Path(deploy_path)
        path_to_solution = self._get_path_to_solution(_deploy_path)

        active_solution = self.album.state_manager().load(path_to_solution)
        active_solution.setup().changelog = changelog

        if catalog_name:
            catalog = self.album.catalogs().get_by_name(catalog_name)
        else:
            raise RuntimeError("No catalog specified for deployment!")

        self._deploy(
            catalog,
            active_solution,
            _deploy_path,
            dry_run,
            force_deploy,
            _push_options,
            git_email,
            git_name,
            no_conda_lock,
        )

        if dry_run:
            module_logger().info(
                "Successfully pretended to deploy %s to %s."
                % (_deploy_path, catalog_name)
            )
        else:
            module_logger().info(
                f"Successfully deployed {_deploy_path} to {catalog_name}."
            )

    def undeploy(
        self,
        solution_to_resolve: str,
        catalog_name: str,
        dry_run: bool,
        push_options: Optional[List[str]] = None,
        git_email: str = "",
        git_name: str = "",
    ) -> None:
        _push_options = push_options if push_options is not None else []

        exit_msg = (
            "Pretending to remove %s from %s..."
            if dry_run
            else "Removing %s from %s..."
        )
        module_logger().info(exit_msg % (solution_to_resolve, catalog_name))

        coordinates = dict_to_coordinates(
            get_attributes_from_string(solution_to_resolve)
        )
        catalog = self.album.catalogs().get_by_name(catalog_name)
        # check for cache catalog only
        if catalog.is_cache():
            raise RuntimeError(
                "Cannot undeploy from catalog only used for caching! Aborting..."
            )

        with catalog.retrieve_catalog(
            self.get_download_path(catalog), force_retrieve=True
        ) as repo:
            # load index
            catalog.set_index_path(
                Path(repo.working_tree_dir).joinpath(
                    DefaultValues.catalog_index_file_name.value
                )
            )
            self.album.migration_manager().load_index(catalog)

            # get versions from catalog
            ordered_version_tags = self._get_tags_for_coordinates(repo, coordinates)
            current_version_tag = (
                ordered_version_tags[0] if len(ordered_version_tags) > 0 else None
            )
            previous_version_tag = (
                ordered_version_tags[1] if len(ordered_version_tags) > 1 else None
            )

            version_to_be_removed = as_tag(coordinates)
            if version_to_be_removed not in ordered_version_tags:
                raise LookupError(
                    "Cannot find %s in deployed versions %s"
                    % (version_to_be_removed, ordered_version_tags)
                )

            self._remove_from_downloaded_catalog(catalog, coordinates, dry_run)

            if not previous_version_tag:
                # remove files from catalog, update db, remove tag
                self._remove_db_entry_and_files(
                    repo, coordinates, dry_run, _push_options, git_email, git_name
                )
            else:
                if current_version_tag == version_to_be_removed:
                    # roll back to last version
                    self._remove_db_entry_and_revert_files(
                        repo,
                        coordinates,
                        previous_version_tag,
                        dry_run,
                        _push_options,
                        git_email,
                        git_name,
                    )
                else:
                    # remove tag, update db
                    self._remove_db_entry_and_tag(
                        repo, coordinates, dry_run, _push_options, git_email, git_name
                    )

        # refresh the local index of the catalog
        self.album.migration_manager().refresh_index(catalog)

        exit_msg = (
            "Successfully pretended to remove %s from %s."
            if dry_run
            else "Successfully removed %s from %s."
        )
        module_logger().info(exit_msg % (solution_to_resolve, catalog_name))

    def _deploy(
        self,
        catalog: ICatalog,
        active_solution: ISolution,
        deploy_path: Path,
        dry_run: bool,
        force_deploy: bool,
        push_options: List[str],
        git_email: str = "",
        git_name: str = "",
        no_conda_lock: bool = False,
    ) -> None:
        # check for cache catalog only
        if catalog.is_cache():
            raise RuntimeError(
                "Cannot deploy to catalog only used for caching! Aborting..."
            )

        dl_path = self.get_download_path(catalog)

        # a catalog is always a repository
        with catalog.retrieve_catalog(dl_path, force_retrieve=True) as repo:
            # load index
            catalog.set_index_path(
                Path(repo.working_tree_dir).joinpath(
                    DefaultValues.catalog_index_file_name.value
                )
            )
            self.album.migration_manager().load_index(catalog)

            # requires a loaded index
            process_changelog_file(catalog, active_solution, deploy_path)

            if catalog.type() == "direct":
                self._deploy_to_direct_catalog(
                    repo,
                    catalog,
                    active_solution,
                    deploy_path,
                    dry_run,
                    force_deploy,
                    push_options,
                    git_email,
                    git_name,
                    no_conda_lock,
                )
            elif catalog.type() == "request":
                self._deploy_to_request_catalog(
                    repo,
                    catalog,
                    active_solution,
                    deploy_path,
                    dry_run,
                    push_options,
                    git_email,
                    git_name,
                    no_conda_lock,
                )
            else:
                raise NotImplementedError("type %s not supported!" % catalog.type())

    def _deploy_to_direct_catalog(
        self,
        repo: Repo,
        catalog: ICatalog,
        active_solution: ISolution,
        deploy_path: Path,
        dry_run: bool,
        force_deploy: bool,
        push_options: List[str],
        git_email: str = "",
        git_name: str = "",
        no_conda_lock: bool = False,
    ):
        # adding solutions in the SQL databse for catalog type "direct" done on user side, hence the timestamp
        active_solution.setup()["timestamp"] = datetime.strftime(
            datetime.now(), "%Y-%m-%dT%H:%M:%S.%f"
        )

        self._add_to_downloaded_catalog(catalog, active_solution, dry_run, force_deploy)

        solution_files = self._deploy_routine_in_local_src(
            catalog, repo, active_solution, deploy_path, no_conda_lock
        )
        commit_files = solution_files + [catalog.index_file_path()]
        solution_root = str(
            self.album.configuration().get_solution_path_suffix_unversioned(
                active_solution.coordinates()
            )
        )

        # merge and push
        if not dry_run:
            try:
                self._push_directly(
                    active_solution.coordinates(),
                    repo,
                    [solution_root],
                    [str(x) for x in commit_files],
                    dry_run,
                    push_options,
                    git_email,
                    git_name,
                )
                add_tag(repo, as_tag(active_solution.coordinates()))
            except Exception as e:
                module_logger().error(
                    "Pushing to catalog failed! Rolling back deployment..."
                )
                try:
                    clean_repository(repo)
                    for export in solution_files:
                        export.unlink()
                finally:
                    raise e

            # refresh the local index of the catalog
            self.album.migration_manager().refresh_index(catalog)
        else:
            module_logger().info(
                "Would commit the changes and push to %s..." % catalog.src()
            )
            module_logger().info("Would refresh the index from src")

    def _deploy_to_request_catalog(
        self,
        repo: Repo,
        catalog: ICatalog,
        active_solution: ISolution,
        deploy_path: Path,
        dry_run: bool,
        push_options: List[str],
        git_email: str = "",
        git_name: str = "",
        no_conda_lock: bool = False,
    ) -> None:
        # include files/folders in catalog
        mr_files = self._deploy_routine_in_local_src(
            catalog, repo, active_solution, deploy_path, no_conda_lock
        )

        if not push_options:
            push_options = retrieve_default_mr_push_options(str(catalog.src()))

        self._create_merge_request(
            active_solution.coordinates(),
            repo,
            [str(x) for x in mr_files],
            dry_run,
            push_options,
            git_email,
            git_name,
        )

    def _deploy_routine_in_local_src(
        self,
        catalog: ICatalog,
        repo: Repo,
        active_solution: ISolution,
        deploy_path: Path,
        no_conda_lock: bool,
    ) -> List[Path]:
        solution_files = self.album.resource_manager().write_solution_files(
            catalog, repo.working_tree_dir, active_solution, deploy_path, no_conda_lock
        )

        return solution_files

    def get_download_path(self, catalog: ICatalog) -> Path:
        return Path(self.album.configuration().cache_path_download()).joinpath(
            catalog.name()
        )

    def _get_tmp_dir(self) -> Path:
        return self.album.configuration().tmp_path()

    @staticmethod
    def _get_tags_for_coordinates(repo: Repo, coordinates: ICoordinates) -> List[str]:
        tags = get_tags(repo)
        tag_start = as_tag_unversioned(coordinates)
        return [tag for tag in tags if tag.startswith(tag_start)]

    @staticmethod
    def _add_to_downloaded_catalog(
        catalog: ICatalog, active_solution: ISolution, dry_run: bool, force_deploy: bool
    ) -> None:
        if not dry_run:
            catalog.add(active_solution, force_overwrite=force_deploy)
        else:
            module_logger().info(
                "Would add the solution %s to index..."
                % active_solution.coordinates().name()
            )

    @staticmethod
    def _remove_from_downloaded_catalog(
        catalog: ICatalog, coordinates: ICoordinates, dry_run: bool
    ) -> None:
        if not dry_run:
            catalog.remove(coordinates)
        else:
            module_logger().info(
                "Would remove the solution %s from index..." % coordinates.name()
            )

    @staticmethod
    def _clear_deploy_target_path(target_path: Path, force_deploy: bool) -> None:
        if target_path.is_dir() and not folder_empty(target_path):
            if force_deploy:
                force_remove(target_path)
            else:
                raise RuntimeError(
                    "The deploy target folder is not empty! Enable --force-deploy to continue!"
                )

    @staticmethod
    def _get_path_to_solution(deploy_path: Path) -> Path:
        if deploy_path.is_dir():
            path_to_solution = deploy_path.joinpath(
                DefaultValues.solution_default_name.value
            )
        else:
            path_to_solution = deploy_path

        return path_to_solution

    @staticmethod
    def retrieve_head_name(coordinates: ICoordinates) -> str:
        return "_".join(
            [coordinates.group(), coordinates.name(), coordinates.version()]
        )

    @staticmethod
    def _create_merge_request(
        coordinates: ICoordinates,
        repo: Repo,
        file_paths: List[str],
        dry_run: bool = False,
        push_option: Optional[List[str]] = None,
        email: str = "",
        username: str = "",
    ):
        if push_option is None:
            push_option = []

        # make a new branch and checkout
        new_head = create_new_head(repo, DeployManager.retrieve_head_name(coordinates))
        new_head.checkout()

        commit_msg = "Adding new/updated %s" % DeployManager.retrieve_head_name(
            coordinates
        )

        add_files_commit_and_push(
            new_head,
            [Path(x) for x in file_paths],
            commit_msg,
            push=not dry_run,
            push_option_list=push_option,
            email=email,
            username=username,
            force=True,
        )

    @staticmethod
    def _push_directly(
        coordinates: ICoordinates,
        repo: Repo,
        files_to_remove: List[str],
        files_to_add: List[str],
        dry_run: Optional[bool] = False,
        push_option: Optional[List[str]] = None,
        email: str = "",
        username: str = "",
    ) -> None:
        if push_option is None:
            push_option = []

        # don't create a new branch. use reference branch from origin
        head = checkout_main(repo)

        commit_msg = "Adding new/updated %s" % DeployManager.retrieve_head_name(
            coordinates
        )
        remove_files(head, files_to_remove)

        add_files_commit_and_push(
            head,
            [Path(x) for x in files_to_add],
            commit_msg,
            push=not dry_run,
            push_option_list=push_option,
            email=email,
            username=username,
            force=False,
        )

    def _remove_db_entry_and_files(
        self,
        repo: Repo,
        coordinates: ICoordinates,
        dry_run: bool,
        push_options: List[str],
        git_email: str,
        git_name: str,
    ) -> None:

        solution_root = str(
            self.album.configuration().get_solution_path_suffix_unversioned(coordinates)
        )
        db_index = DefaultValues.catalog_index_file_name.value

        init_msg = (
            "Would remove files %s, would update %s.."
            if dry_run
            else "Removing files %s, updating %s.."
        )
        module_logger().info(init_msg % (solution_root, db_index))

        if not dry_run:
            self._try_push_remove_tag(
                coordinates,
                repo,
                [solution_root],
                [db_index],
                push_options,
                git_email,
                git_name,
            )

    def _remove_db_entry_and_revert_files(
        self,
        repo: Repo,
        coordinates: ICoordinates,
        previous_version_tag: str,
        dry_run: bool,
        push_options: List[str],
        git_email: str,
        git_name: str,
    ) -> None:

        solution_root = str(
            self.album.configuration().get_solution_path_suffix_unversioned(coordinates)
        )
        db_index = DefaultValues.catalog_index_file_name.value

        init_msg = (
            "Would revert %s to %s, would update %s.."
            if dry_run
            else "Reverting %s to %s, updating %s.."
        )
        module_logger().info(init_msg % (solution_root, previous_version_tag, db_index))

        if not dry_run:
            revert(repo, previous_version_tag, [solution_root])
            self._try_push_remove_tag(
                coordinates, repo, [], [db_index], push_options, git_email, git_name
            )

    def _remove_db_entry_and_tag(
        self,
        repo: Repo,
        coordinates: ICoordinates,
        dry_run: bool,
        push_options: List[str],
        git_email: str,
        git_name: str,
    ):
        db_index = DefaultValues.catalog_index_file_name.value

        init_msg = "Would update %s.." if dry_run else "Updating %s.."
        module_logger().info(init_msg % (db_index))

        if not dry_run:
            self._try_push_remove_tag(
                coordinates, repo, [], [db_index], push_options, git_email, git_name
            )

    def _try_push_remove_tag(
        self,
        coordinates: ICoordinates,
        repo: Repo,
        files_to_remove: List[str],
        files_to_add: List[str],
        push_options: List[str],
        git_email: str,
        git_name: str,
    ):
        try:
            if push_options is None:
                push_options = []

            # don't create a new branch. use reference branch from origin
            head = checkout_main(repo)

            commit_msg = "Removing %s" % DeployManager.retrieve_head_name(coordinates)

            remove_tag(repo, as_tag(coordinates))

            remove_files(head, files_to_remove)

            add_files_commit_and_push(
                head,
                [Path(x) for x in files_to_add],
                commit_msg,
                push=True,
                push_option_list=push_options,
                email=git_email,
                username=git_name,
                force=False,
            )
        except Exception as e:
            module_logger().error(
                "Pushing to catalog failed! Rolling back deployment..."
            )
            try:
                clean_repository(repo)
            finally:
                raise e
