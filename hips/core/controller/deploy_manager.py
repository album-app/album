from pathlib import Path

import yaml

from hips.core import load
from hips.core.model.catalog_configuration import HipsCatalogCollection
from hips.core.utils.operations.file_operations import create_path_recursively, copy
from hips.core.utils.operations.git_operations import create_new_head, add_files_commit_and_push

from hips_runner import logging

module_logger = logging.get_active_logger


class DeployManager:
    catalog_configuration = None
    active_hips = None
    repo = None

    def __init__(self):
        self.catalog_configuration = HipsCatalogCollection()
        self._catalog = None

    # Todo: write tests
    def deploy(self, path, catalog,  dry_run, trigger_pipeline):
        """Function corresponding to the `deploy` subcommand of `hips`.

        Generates the yml for a hips and creates a merge request to the catalog only
        including the markdown and solution file.

        """
        self.active_hips = load(path)
        self._catalog = catalog

        # run installation of new solution file in debug mode
        # Todo: call the installation routine?

        if self._catalog:
            self._catalog = self.catalog_configuration.get_catalog_by_id(self._catalog)
        elif self.active_hips["deploy"] and self.active_hips["deploy"]["catalog"]:
            self._catalog = self.catalog_configuration.get_deployment_catalog(
                self.active_hips["deploy"]["catalog"]
            )
        else:
            self._catalog = self.catalog_configuration.get_default_deployment_catalog()

        if not self._catalog.is_local:
            self.repo = self._catalog.download()

        # copy script to repository or catalog
        if self._catalog.is_local:
            solution_file = self._copy_solution_in_catalog(path)
        else:
            solution_file = self._copy_solution_to_repository(path)

        # create solution yml file
        if not self._catalog.is_local:
            yml_file = self._create_yaml_file_in_repo()

            # create merge request
            self._create_hips_merge_request([yml_file, solution_file], dry_run, trigger_pipeline)

    def retrieve_head_name(self):
        return "_".join([self.active_hips["group"], self.active_hips["name"], self.active_hips["version"]])

    def _create_hips_merge_request(self, file_paths, dry_run=False, trigger_pipeline=True):
        """Creates a merge request to the catalog repository for the hips object.

        Commits first the files given in the call, but will not include anything else than that.

        Args:
            file_paths:
                A list of files to include in the merge request. Can be relative to the catalog repository path or absolute.
            dry_run:
                Option to only show what would happen. No Merge request will be created.

        Raises:
            RuntimeError when no differences to the previous commit can be found.

        """
        # make a new branch and checkout

        new_head = create_new_head(self.repo, self.retrieve_head_name())
        new_head.checkout()

        commit_msg = "Adding new/updated %s" % self.retrieve_head_name()

        add_files_commit_and_push(new_head, file_paths, commit_msg, dry_run, trigger_pipeline)

    def _create_yaml_file_in_repo(self):
        """Creates a Markdown file in the given repo for the given solution.

        Args:
            repo:
                The repo of the catalog.

        Returns:
            The Path to the created markdown file.

        """
        yaml_str = self._create_yml_string()

        yaml_path = Path(self.repo.working_tree_dir).joinpath(
            "catalog",
            self.active_hips['group'],
            self.active_hips["name"],
            self.active_hips["version"],
            "%s%s" % (self.active_hips['name'], ".yml")
        )

        create_path_recursively(yaml_path.parent)

        module_logger().info('writing to: %s...' % yaml_path)
        with open(yaml_path, 'w') as f:
            f.write(yaml_str)

        return yaml_path

    def _create_yml_string(self):
        """Creates the yaml string with all relevant information"""
        d = self.active_hips.get_hips_deploy_dict()
        module_logger().debug('Create yaml file from solution...')
        return yaml.dump(d, Dumper=yaml.Dumper)  # todo: move to file operation

    def _copy_solution_to_repository(self, path):
        """Copies a solution outside the catalog repository to the correct path inside the catalog repository.

        Returns:
            The path to the solution file in the correct folder inside the catalog repository.

        """
        abs_path_solution_file = Path(self.repo.working_tree_dir).joinpath(
            "solutions",  # todo: replace with default value!
            self.active_hips['group'],
            self.active_hips["name"],
            self.active_hips["version"],
            "%s%s" % (self.active_hips['name'], ".py")
        )
        module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_file))
        copy(path, abs_path_solution_file)

        return abs_path_solution_file

    def _copy_solution_in_catalog(self, path):
        abs_path_solution_file = self._catalog.get_solution_cache_file(
            self.active_hips.group, self.active_hips.name, self.active_hips.version
        )
        module_logger().debug("Copying %s to %s..." % (path, abs_path_solution_file))
        copy(path, abs_path_solution_file)

        return abs_path_solution_file
