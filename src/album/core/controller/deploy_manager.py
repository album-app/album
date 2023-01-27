import os
from datetime import datetime
from pathlib import Path

from git import Repo

from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.deploy_manager import IDeployManager
from album.core.api.model.catalog import ICatalog
from album.core.model.default_values import DefaultValues
from album.core.utils.export.changelog import (
    create_changelog_file,
    process_changelog_file,
)
from album.core.utils.operations.file_operations import (
    copy,
    write_dict_to_yml,
    force_remove,
    folder_empty,
)
from album.core.utils.operations.git_operations import (
    create_new_head,
    add_files_commit_and_push,
    retrieve_default_mr_push_options,
    checkout_main,
    clean_repository,
    remove_files,
    remove_tag,
    add_tag,
    get_tags,
    revert,
)
from album.core.utils.operations.resolve_operations import (
    get_attributes_from_string,
    dict_to_coordinates,
    as_tag_unversioned,
    as_tag,
)
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner import album_logging
from album.runner.core.api.model.coordinates import ICoordinates
from album.runner.core.api.model.solution import ISolution

module_logger = album_logging.get_active_logger


class DeployManager(IDeployManager):
    def __init__(self, album: IAlbumController):
        self.album = album

    def deploy(
        self,
        deploy_path,
        catalog_name: str,
        dry_run: bool,
        push_options=None,
        git_email: str = None,
        git_name: str = None,
        force_deploy: bool = False,
        changelog: str = None,
    ):
        if dry_run:
            module_logger().info(
                "Pretending to deploy %s to %s..." % (deploy_path, catalog_name)
            )
        else:
            module_logger().info("Deploying %s to %s..." % (deploy_path, catalog_name))

        deploy_path = Path(deploy_path)
        path_to_solution = self._get_path_to_solution(deploy_path)

        active_solution = self.album.state_manager().load(path_to_solution)
        active_solution.setup().changelog = changelog

        if catalog_name:
            catalog = self.album.catalogs().get_by_name(catalog_name)
        else:
            raise RuntimeError("No catalog specified for deployment!")

        self._deploy(
            catalog,
            active_solution,
            deploy_path,
            dry_run,
            force_deploy,
            push_options,
            git_email,
            git_name,
        )

        if dry_run:
            module_logger().info(
                "Successfully pretended to deploy %s to %s."
                % (deploy_path, catalog_name)
            )
        else:
            module_logger().info(
                "Successfully deployed %s to %s." % (deploy_path, catalog_name)
            )

    def undeploy(
        self,
        solution_to_resolve,
        catalog_name: str,
        dry_run: bool,
        push_options=None,
        git_email: str = None,
        git_name: str = None,
    ):

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
            if not version_to_be_removed in ordered_version_tags:
                raise LookupError(
                    "Cannot find %s in deployed versions %s"
                    % (version_to_be_removed, ordered_version_tags)
                )

            self._remove_from_downloaded_catalog(catalog, coordinates, dry_run)

            if not previous_version_tag:
                # remove files from catalog, update db, remove tag
                self._remove_db_entry_and_files(
                    repo, coordinates, dry_run, push_options, git_email, git_name
                )
            else:
                if current_version_tag == version_to_be_removed:
                    # roll back to last version
                    self._remove_db_entry_and_revert_files(
                        repo,
                        coordinates,
                        previous_version_tag,
                        dry_run,
                        push_options,
                        git_email,
                        git_name,
                    )
                else:
                    # remove tag, update db
                    self._remove_db_entry_and_tag(
                        repo, coordinates, dry_run, push_options, git_email, git_name
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
        push_options: list,
        git_email=None,
        git_name=None,
    ):
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
        push_options: list,
        git_email=None,
        git_name=None,
    ):
        """Routine to deploy to a direct catalog"""
        # adding solutions in the SQL databse for catalog type "direct" done on user side, hence the timestamp
        active_solution.setup()["timestamp"] = datetime.strftime(
            datetime.now(), "%Y-%m-%dT%H:%M:%S.%f"
        )

        self._add_to_downloaded_catalog(catalog, active_solution, dry_run, force_deploy)

        solution_files = self._deploy_routine_in_local_src(
            catalog, repo, active_solution, deploy_path
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
                    commit_files,
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
        push_options: list,
        git_email=None,
        git_name=None,
    ):
        """Routine to deploy to a request catalog."""

        # include files/folders in catalog
        mr_files = self._deploy_routine_in_local_src(
            catalog, repo, active_solution, deploy_path
        )

        if not push_options:
            push_options = retrieve_default_mr_push_options(catalog.src())

        self._create_merge_request(
            active_solution.coordinates(),
            repo,
            mr_files,
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
    ):
        """Performs all routines a deploy process needs to do locally.

        Returns:
            solution zip file and additional attachments.

        """
        solution_files = self._collect_solution_files(
            catalog, repo.working_tree_dir, active_solution, deploy_path
        )

        return solution_files

    def get_download_path(self, catalog: ICatalog):
        return Path(self.album.configuration().cache_path_download()).joinpath(
            catalog.name()
        )

    def _collect_solution_files(
        self,
        catalog: ICatalog,
        catalog_local_src: str,
        active_solution: ISolution,
        deploy_path: Path,
    ):
        coordinates = active_solution.coordinates()

        catalog_solution_local_src_path = Path(catalog_local_src).joinpath(
            self.album.configuration().get_solution_path_suffix_unversioned(coordinates)
        )

        res = []
        if deploy_path.is_file():
            solution_path = catalog_solution_local_src_path.joinpath(
                DefaultValues.solution_default_name.value
            )
            res.append(copy(deploy_path, solution_path))
        else:
            for subdir, dirs, files in os.walk(deploy_path):
                for file in files:
                    filepath = subdir + os.sep + file
                    rel_path = os.path.relpath(filepath, deploy_path)
                    target = catalog_solution_local_src_path.joinpath(rel_path)
                    res.append(copy(filepath, target))

        res.append(
            self._create_yaml_file_in_local_src(
                active_solution, catalog_solution_local_src_path
            )
        )
        res.append(
            create_changelog_file(
                active_solution, catalog, catalog_solution_local_src_path
            )
        )

        return res

    def _get_tmp_dir(self):
        return self.album.configuration().tmp_path()

    @staticmethod
    def _get_tags_for_coordinates(repo, coordinates: ICoordinates):
        tags = get_tags(repo)
        tag_start = as_tag_unversioned(coordinates)
        return [tag for tag in tags if tag.startswith(tag_start)]

    @staticmethod
    def _add_to_downloaded_catalog(
        catalog: ICatalog, active_solution: ISolution, dry_run: bool, force_deploy: bool
    ):
        """Updates the index in the downloaded repository!"""
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
    ):
        """Updates the index in the downloaded repository!"""
        if not dry_run:
            catalog.remove(coordinates)
        else:
            module_logger().info(
                "Would remove the solution %s from index..." % coordinates.name()
            )

    @staticmethod
    def _clear_deploy_target_path(target_path: Path, force_deploy: bool):
        """Clears the target path (locally) where the solution is supposed to be deployed to."""
        if target_path.is_dir() and not folder_empty(target_path):
            if force_deploy:
                force_remove(target_path)
            else:
                raise RuntimeError(
                    "The deploy target folder is not empty! Enable --force-deploy to continue!"
                )

    @staticmethod
    def _get_path_to_solution(deploy_path: Path):
        """Gets the path to the solution behind the deploy_path. If folder is provided file called solution.py must
        live in the deploy_path.
        """
        if deploy_path.is_dir():
            path_to_solution = deploy_path.joinpath(
                DefaultValues.solution_default_name.value
            )
        else:
            path_to_solution = deploy_path

        return path_to_solution

    @staticmethod
    def retrieve_head_name(coordinates: ICoordinates):
        """Retrieves the branch (head) name for the merge request of the solution file."""
        return "_".join(
            [coordinates.group(), coordinates.name(), coordinates.version()]
        )

    @staticmethod
    def _create_merge_request(
        coordinates: ICoordinates,
        repo: Repo,
        file_paths,
        dry_run=False,
        push_option=None,
        email=None,
        username=None,
    ):
        """Creates a merge request to the catalog repository for the album object.

        Commits first the files given in the call, but will not include anything else than that.

        Args:
            file_paths:
                A list of files to include in the merge request. Can be relative to
                the catalog repository path or absolute.
            dry_run:
                Option to only show what would happen. No Merge request will be created.
            push_option:
                Push options for the repository.
            username:
                The git user to use. (Default: systems git configuration)
            email:
                The git email to use. (Default: systems git configuration)

        Raises:
            RuntimeError when no differences to the previous commit can be found.

        """
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
            file_paths,
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
        files_to_remove: list,
        files_to_add: list,
        dry_run=False,
        push_option=None,
        email=None,
        username=None,
    ):
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
            files_to_add,
            commit_msg,
            push=not dry_run,
            push_option_list=push_option,
            email=email,
            username=username,
            force=False,
        )

    @staticmethod
    def _create_yaml_file_in_local_src(active_solution: ISolution, solution_home: Path):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        yaml_path = solution_home.joinpath(
            DefaultValues.solution_yml_default_name.value
        )

        module_logger().debug("Writing yaml file to: %s..." % yaml_path)
        write_dict_to_yml(yaml_path, get_deploy_dict(active_solution))

        return yaml_path

    def _remove_db_entry_and_files(
        self, repo, coordinates, dry_run, push_options, git_email, git_name
    ):

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
        repo,
        coordinates,
        previous_version_tag,
        dry_run,
        push_options,
        git_email,
        git_name,
    ):

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
        self, repo, coordinates, dry_run, push_options, git_email, git_name
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
        coordinates,
        repo,
        files_to_remove,
        files_to_add,
        push_options,
        git_email,
        git_name,
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
                files_to_add,
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
