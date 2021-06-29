from pathlib import Path

from hips.core.concept.singleton import Singleton

from hips.core import load
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import copy, write_dict_to_yml
from hips.core.utils.operations.git_operations import create_new_head, add_files_commit_and_push
from hips_runner import logging

module_logger = logging.get_active_logger


class DeployManager(metaclass=Singleton):
    """Class handling the deployment process.

    During deployment, a solution file will be requested to be added to a catalog. This catalog must be configured or
    specified in the solution file.
    When deploying to a remote catalog, deployment happens via a merge request to the git repository of the catalog.
    A deployment can also be requested to a catalog only existing locally.
    In this case, no merge request will be created!

    Attributes:
        catalog_collection:
            Holding all configured catalogs.

    Notes:
        Git credentials required when deploying to a remote catalog!

    """
    # singletons
    catalog_collection = None

    def __init__(self, catalog_collection=None):
        self.catalog_collection = HipsCatalogCollection() if not catalog_collection else catalog_collection
        self._catalog = None
        self._active_hips = None
        self._repo = None

    def deploy(self, path, catalog, dry_run, trigger_pipeline, git_email=None, git_name=None):
        """Function corresponding to the `deploy` subcommand of `hips`.

        Generates the yml for a hips and creates a merge request to the catalog only
        including the yaml and solution file.

        Args:
            path:
                Path to the solution.
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
        self._active_hips = load(path)

        if catalog:  # case catalog given
            self._catalog = self.catalog_collection.get_catalog_by_id(catalog)
        elif self._active_hips["deploy"] and self._active_hips["deploy"]["catalog"]:
            self._catalog = self.catalog_collection.get_catalog_by_url(
                self._active_hips["deploy"]["catalog"]["url"]
            )
        else:
            self._catalog = self.catalog_collection.get_default_deployment_catalog()
            module_logger().warning("No catalog specified. Deploying to default catalog %s!" % self._catalog.id)

        if self._catalog.is_local:
            self._copy_solution_in_catalog(path)
        else:
            dl_path = Path(self.catalog_collection.configuration.cache_path_download).joinpath(self._catalog.id)
            self._repo = self._catalog.download(dl_path, force_download=True)

            if not self._repo:
                raise FileNotFoundError("Repository not found. Did the download fail?")

            solution_file = self._copy_solution_to_repository(path)

            yml_file = self._create_yaml_file_in_repo()

            # create merge request
            self._create_hips_merge_request([yml_file, solution_file], dry_run, trigger_pipeline, git_email, git_name)

    def retrieve_head_name(self):
        """Retrieves the branch (head) name for the merge request of the solution file."""
        return "_".join([self._active_hips["group"], self._active_hips["name"], self._active_hips["version"]])

    def _create_hips_merge_request(self, file_paths, dry_run=False, trigger_pipeline=True, email=None, username=None):
        """Creates a merge request to the catalog repository for the hips object.

        Commits first the files given in the call, but will not include anything else than that.

        Args:
            file_paths:
                A list of files to include in the merge request. Can be relative to the catalog repository path or absolute.
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

        add_files_commit_and_push(new_head, file_paths, commit_msg, dry_run, trigger_pipeline, email, username)

    def _create_yaml_file_in_repo(self):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        yaml_path = Path(self._repo.working_tree_dir).joinpath(
            HipsDefaultValues.catalog_yaml_prefix.value,
            self._active_hips['group'],
            self._active_hips["name"],
            self._active_hips["version"],
            "%s%s" % (self._active_hips['name'], ".yml")
        )

        module_logger().info('writing yaml file to: %s...' % yaml_path)
        write_dict_to_yml(yaml_path, self._active_hips.get_hips_deploy_dict())

        return yaml_path

    def _copy_solution_to_repository(self, path):
        """Copies a solution outside the catalog repository to the correct path inside the catalog repository.

        Returns:
            The path to the solution file in the correct folder inside the catalog repository.

        """
        abs_path_solution_file = Path(self._repo.working_tree_dir).joinpath(
            self._catalog.get_solution_cache_file_suffix(
                self._active_hips['group'],
                self._active_hips["name"],
                self._active_hips["version"]
            )
        )
        module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_file))
        copy(path, abs_path_solution_file)

        return abs_path_solution_file

    def _copy_solution_in_catalog(self, path):
        """Copies a solution to the catalog.

        Args:
            path:
                The path to copy the solution to.

        Returns:
            The absolute path of the destination file.

        """
        abs_path_solution_file = self._catalog.get_solution_cache_file(
            self._active_hips.group, self._active_hips.name, self._active_hips.version
        )
        module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_file))
        copy(path, abs_path_solution_file)

        return abs_path_solution_file
