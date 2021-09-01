import os
import tempfile
from pathlib import Path

from album.core import load
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations import file_operations
from album.core.utils.operations.file_operations import copy, write_dict_to_yml, zip_folder, zip_paths
from album.core.utils.operations.git_operations import create_new_head, add_files_commit_and_push
from album.core.utils.operations.resolve_operations import solution_to_group_name_version
from album_runner import logging

module_logger = logging.get_active_logger


class DeployManager(metaclass=Singleton):
    """Class handling the deployment process.

    During deployment, a solution file will be requested to be added to a catalog. This catalog must be configured or
    specified in the solution file.
    When deploying to a remote catalog, deployment happens via a merge request to the git repository of the catalog.
    A deployment can also be requested to a catalog only existing locally.
    In this case, no merge request will be created!

    Attributes:
        collection_manager:
            Holding all configured catalogs.

    Notes:
        Git credentials required when deploying to a remote catalog!

    """
    # singletons
    collection_manager = None

    def __init__(self):
        self.collection_manager = CollectionManager()
        self._catalog = None
        self._active_solution = None
        self._catalog_local_src = None
        self._repo = None

    def deploy(self, deploy_path, catalog_name, dry_run, trigger_pipeline, git_email=None, git_name=None):
        """Function corresponding to the `deploy` subcommand of `album`.

        Generates the yml for a album and creates a merge request to the catalog only
        including the yaml and solution file.

        Args:
            deploy_path:
                Path to a directory or a file.
                If directory: Must contain "solution.py" file.
            catalog_name:
                The catalog to deploy to. Either specify via argument in deploy-call, via url in solution or use
                default catalog.
            dry_run:
                Boolean indicates whether to just show what would happen if.
            trigger_pipeline:
                Boolean to trigger the CI pipeline (True) or not (False).
            git_email:
                The git email to use. (Default: systems git configuration)
            git_name:
                The git user to use. (Default: systems git configuration)

        """
        deploy_path = Path(deploy_path)

        if deploy_path.is_dir():
            path_to_solution = deploy_path.joinpath(DefaultValues.solution_default_name.value)
        else:
            path_to_solution = deploy_path

        self._active_solution = load(path_to_solution)

        if catalog_name:  # case catalog given
            self._catalog = self.collection_manager.catalogs().get_by_name(catalog_name)
        elif self._active_solution["deploy"] and self._active_solution["deploy"]["catalog"]:
            self._catalog = self.collection_manager.catalogs().get_by_src(
                self._active_solution["deploy"]["catalog"]["src"]
            )
        else:
            raise RuntimeError("No catalog specified for deployment")

        self._catalog.load_index()

        if self._catalog.is_local():
            if self._catalog.is_cache():
                raise RuntimeError("Cannot deploy to catalog only used for caching")
            self._catalog_local_src = self._catalog.src
            # zip solution folder, create a yml file and copy the cover
            self._copy_and_zip(deploy_path)
            self._create_yaml_file_in_local_src()
            self._copy_cover_to_local_src(deploy_path)
            self._catalog.catalog_index.update(self._active_solution.get_deploy_dict())
            self._catalog.catalog_index.get_connection().commit()
            self._catalog.catalog_index.export(self._catalog.solution_list_path)
            self._catalog.copy_index_from_cache_to_src()
            self._catalog.refresh_index()
        else:
            dwnld_path = Path(self.collection_manager.configuration.cache_path_download).joinpath(self._catalog.name)
            repo = self._catalog.retrieve_catalog(dwnld_path, force_retrieve=True)
            self._repo = self._update_repo(repo)

            if not self._repo:
                raise FileNotFoundError("Catalog repository not found. Did the download of the catalog fail?")

            # zip solution folder, create a yml file and copy the cover
            solution_zip = self._copy_and_zip(deploy_path)
            yml_file = self._create_yaml_file_in_local_src()
            cover_files = self._copy_cover_to_local_src(deploy_path)

            # merge request files:
            mr_files = [yml_file, solution_zip] + cover_files

            # create merge request
            self._create_merge_request(mr_files, dry_run, trigger_pipeline, git_email, git_name)

    def retrieve_head_name(self):
        """Retrieves the branch (head) name for the merge request of the solution file."""
        return "_".join(
            [self._active_solution["group"], self._active_solution["name"], self._active_solution["version"]]
        )

    def _update_repo(self, repo):
        self._catalog_local_src = repo.working_tree_dir
        return repo

    def _create_merge_request(self, file_paths, dry_run=False, trigger_pipeline=True, email=None, username=None):
        """Creates a merge request to the catalog repository for the album object.

        Commits first the files given in the call, but will not include anything else than that.

        Args:
            file_paths:
                A list of files to include in the merge request. Can be relative to
                the catalog repository path or absolute.
            dry_run:
                Option to only show what would happen. No Merge request will be created.
            trigger_pipeline:
                Boolean, whether to start CI pipeline or not.
            username:
                The git user to use. (Default: systems git configuration)
            email:
                The git email to use. (Default: systems git configuration)

        Raises:
            RuntimeError when no differences to the previous commit can be found.

        """
        # make a new branch and checkout

        new_head = create_new_head(self._repo, self.retrieve_head_name())
        new_head.checkout()

        commit_msg = "Adding new/updated %s" % self.retrieve_head_name()

        add_files_commit_and_push(new_head, file_paths, commit_msg, not dry_run, trigger_pipeline, email, username)

    def _get_cache_suffix(self):
        return Path(self._catalog_local_src).joinpath(
            self._catalog.get_solution_zip_suffix(
                solution_to_group_name_version(self._active_solution)
            )
        )

    def _create_yaml_file_in_local_src(self):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        yaml_path = Path(self._catalog_local_src).joinpath(
            DefaultValues.catalog_yaml_prefix.value,
            self._active_solution['group'],
            self._active_solution["name"],
            self._active_solution["version"],
            "%s%s" % (self._active_solution['name'], ".yml")
        )

        module_logger().info('writing yaml file to: %s...' % yaml_path)
        write_dict_to_yml(yaml_path, self._active_solution.get_deploy_dict())

        return yaml_path

    def _copy_and_zip(self, folder_path):
        """Copies the deploy-file or -folder to the catalog repository."""
        zip_path = self._get_cache_suffix()
        if folder_path.is_dir():
            return zip_folder(folder_path, zip_path)
        if folder_path.is_file():
            tmp_dir = tempfile.TemporaryDirectory()
            tmp_solution_file = Path(tmp_dir.name).joinpath(DefaultValues.solution_default_name.value)
            copy(folder_path, tmp_solution_file)
            return zip_paths([tmp_solution_file], zip_path)

    def _copy_cover_to_local_src(self, folder_path):
        """Copies all cover files to the repo."""
        target_path = self._get_cache_suffix().parent
        cover_list = []

        if hasattr(self._active_solution, "covers"):
            for cover in self._active_solution["covers"]:
                cover_name = cover["source"]
                cover_path = folder_path.joinpath(cover_name)  # relative paths only
                if cover_path.exists():
                    cover_list.append(copy(cover_path, target_path.joinpath(cover_name)))
                else:
                    module_logger().warn(f"Cannot find cover {cover_path.absolute()}, proceeding without copying it.")
        return cover_list
