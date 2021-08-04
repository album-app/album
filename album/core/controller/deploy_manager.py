import os
from pathlib import Path

from album.core import load
from album.core.concept.singleton import Singleton
from album.core.controller.catalog_manager import CatalogManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy, write_dict_to_yml, zip_folder, copy_folder, zip_paths
from album.core.utils.operations.git_operations import create_new_head, add_files_commit_and_push
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
        catalog_manager:
            Holding all configured catalogs.

    Notes:
        Git credentials required when deploying to a remote catalog!

    """
    # singletons
    catalog_manager = None

    def __init__(self):
        self.catalog_manager = CatalogManager()
        self._catalog = None
        self._active_solution = None
        self._repo = None

    def deploy(self, deploy_path, catalog, dry_run, trigger_pipeline, git_email=None, git_name=None):
        """Function corresponding to the `deploy` subcommand of `album`.

        Generates the yml for a album and creates a merge request to the catalog only
        including the yaml and solution file.

        Args:
            deploy_path:
                Path to a directory or a file.
                If directory: Must contain "solution.py" file.
            catalog:
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

        if catalog:  # case catalog given
            self._catalog = self.catalog_manager.get_catalog_by_id(catalog)
        elif self._active_solution["deploy"] and self._active_solution["deploy"]["catalog"]:
            self._catalog = self.catalog_manager.get_catalog_by_url(
                self._active_solution["deploy"]["catalog"]["url"]
            )
        else:
            raise RuntimeError("No catalog specified for deployment")

        if self._catalog.is_local:
            # copy to correct place and add to index for later usage/installation
            self._copy_folder_in_local_catalog(deploy_path)
            self._catalog.add(self._active_solution, force_overwrite=True)
        else:
            dwnld_path = Path(self.catalog_manager.configuration.cache_path_download).joinpath(self._catalog.id)
            self._repo = self._catalog.download(dwnld_path, force_download=True)

            if not self._repo:
                raise FileNotFoundError("Catalog repository not found. Did the download of the catalog fail?")

            # zip solution folder, create a yml file and copy the cover
            solution_zip = self._copy_and_zip(deploy_path)
            yml_file = self._create_yaml_file_in_repo()
            cover_files = self._copy_cover_to_repo(deploy_path)

            # merge request files:
            mr_files = [yml_file, solution_zip] + cover_files

            # create merge request
            self._create_merge_request(mr_files, dry_run, trigger_pipeline, git_email, git_name)

    def retrieve_head_name(self):
        """Retrieves the branch (head) name for the merge request of the solution file."""
        return "_".join(
            [self._active_solution["group"], self._active_solution["name"], self._active_solution["version"]]
        )

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
        return Path(self._repo.working_tree_dir).joinpath(
            self._catalog.get_solution_zip_suffix(
                self._active_solution['group'],
                self._active_solution["name"],
                self._active_solution["version"]
            )
        )

    def _create_yaml_file_in_repo(self):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        yaml_path = Path(self._repo.working_tree_dir).joinpath(
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
            return zip_paths([folder_path], zip_path)

    def _copy_cover_to_repo(self, folder_path):
        """Copies all cover files to the repo."""
        target_path = self._get_cache_suffix().parent
        cover_list = []

        if hasattr(self._active_solution, "covers"):
            for cover in self._active_solution["covers"]:
                cover = Path(cover)
                cover_name = os.path.split(cover)[-1]

                cover_path = folder_path.joinpath(cover)  # relative paths only
                cover_list.append(copy(cover_path, target_path.joinpath(cover_name)))

        return cover_list

    def _copy_folder_in_local_catalog(self, path):
        """Copies a solution folder in the local catalog thereby renaming it."""
        grp = self._active_solution.group
        name = self._active_solution.name
        version = self._active_solution.version

        abs_path_solution_folder = self._catalog.get_solution_path(grp, name, version).joinpath(
            "_".join([grp, name, version])
        )

        if path.is_file():
            abs_path_solution_file = abs_path_solution_folder.joinpath(DefaultValues.solution_default_name.value)

            module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_file))
            return copy(path, abs_path_solution_file)

        module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_folder))
        return copy_folder(path, abs_path_solution_folder, copy_root_folder=False)
