import pkgutil
import tempfile
from datetime import datetime
from pathlib import Path

from git import Repo

import album
from album.core import load
from album.core.concept.singleton import Singleton
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.migration_manager import MigrationManager
from album.core.model.catalog import Catalog
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy, write_dict_to_yml, zip_folder, zip_paths, copy_in_file, \
    create_path_recursively
from album.core.utils.operations.git_operations import create_new_head, add_files_commit_and_push
from album.core.utils.operations.resolve_operations import get_zip_name
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner import album_logging, Solution

module_logger = album_logging.get_active_logger


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

    def deploy(self, deploy_path, catalog_name: str, dry_run: bool, push_option=None, git_email: str = None, git_name: str = None,
               force_deploy: bool = False, change_log: str = ""):
        """Function corresponding to the `deploy` subcommand of `album`.

        Generates the yml for a album and creates a merge request to the catalog only
        including the yaml and solution file.

        Args:
            force_deploy:
                Force overwrites a existing solution during deployment. Only for local catalogs.
            deploy_path:
                Path to a directory or a file.
                If directory: Must contain "solution.py" file.
            catalog_name:
                The catalog to deploy to. Either specify via argument in deploy-call, via url in solution or use
                default catalog.
            dry_run:
                When set, prepares deployment in local src of the catlog (creating zip, docker, yml),
                but not adding to the catalog src.
            push_option:
                Push options for the catalog repository.
            git_email:
                The git email to use. (Default: systems git configuration)
            git_name:
                The git user to use. (Default: systems git configuration)
            change_log:
                The change associated with this version of a solution compared to the last version.

        """
        if dry_run:
            module_logger().info('Pretending to deploy %s to %s...' % (deploy_path, catalog_name))
        else:
            module_logger().info('Deploying %s to %s...' % (deploy_path, catalog_name))

        deploy_path = Path(deploy_path)

        if deploy_path.is_dir():
            path_to_solution = deploy_path.joinpath(DefaultValues.solution_default_name.value)
        else:
            path_to_solution = deploy_path

        active_solution = load(path_to_solution)
        active_solution.setup["changelog"] = change_log

        # case catalog given
        if catalog_name:
            catalog = self.collection_manager.catalogs().get_by_name(catalog_name)

        # case catalog in solution file specified
        # TODO: discuss this
        elif active_solution.setup.deploy and active_solution.setup.deploy["catalog"]:
            catalog = self.collection_manager.catalogs().get_by_src(
                active_solution.setup.deploy["catalog"]["src"]
            )

        # case no catalog given
        else:
            raise RuntimeError("No catalog specified for deployment")

        MigrationManager().load_index(catalog)

        if catalog.is_local():
            self._deploy_to_local_catalog(catalog, active_solution, deploy_path, dry_run, force_deploy)
        else:
            self._deploy_to_remote_catalog(
                catalog, active_solution, deploy_path, dry_run, push_option, git_email, git_name
            )

        if dry_run:
            module_logger().info('Successfully pretended to deploy %s to %s.' % (deploy_path, catalog_name))
        else:
            module_logger().info('Successfully deployed %s to %s.' % (deploy_path, catalog_name))

    def _deploy_to_remote_catalog(self, catalog: Catalog, active_solution: Solution, deploy_path, dry_run, push_option,
                                  git_email=None, git_name=None):
        """Routine to deploy to a remote catalog."""
        dl_path = self.get_download_path(catalog)

        repo = catalog.retrieve_catalog(dl_path, force_retrieve=True)
        catalog_local_src = repo.working_tree_dir

        if not repo:
            raise FileNotFoundError("Catalog repository not found. Did the download of the catalog fail?")

        # include files/folders in catalog
        solution_zip, exports = self._deploy_routine_in_local_src(
            catalog, catalog_local_src, active_solution, deploy_path
        )

        # merge request files:
        mr_files = [solution_zip] + exports

        # create merge request
        self._create_merge_request(active_solution, repo, mr_files, dry_run, push_option, git_email, git_name)

        repo.close()

    def get_download_path(self, catalog: Catalog):
        return Path(self.collection_manager.configuration.cache_path_download).joinpath(catalog.name)

    def _deploy_to_local_catalog(self, catalog: Catalog, active_solution: Solution, deploy_path, dry_run: bool,
                                 force_deploy: bool):
        """Routine to deploy to a local catalog."""
        # check for cache catalog only
        if catalog.is_cache():
            raise RuntimeError("Cannot deploy to catalog only used for caching! Aborting...")

        catalog_local_src = catalog.src
        active_solution.setup["timestamp"] = datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')

        # update the index
        if not dry_run:
            catalog.add(active_solution, force_overwrite=force_deploy)
        else:
            module_logger().info("Would add the solution %s to index..." % active_solution.coordinates.name)

        # include files/folders in catalog
        DeployManager._deploy_routine_in_local_src(catalog, catalog_local_src, active_solution, deploy_path)

        # copy to source
        if not dry_run:
            catalog.copy_index_from_cache_to_src()

            # refresh the local index of the catalog
            MigrationManager().refresh_index(catalog)
        else:
            module_logger().info(
                "Would copy the index to src %s to %s..." % (catalog_local_src, catalog.src)
            )
            module_logger().info(
                "Would refresh the index from src"
            )

    @staticmethod
    def _deploy_routine_in_local_src(catalog, catalog_local_src, active_solution, deploy_path):
        """Performs all routines a deploy process needs to do locally.

        Returns:
            solution zip file, solution docker file, solution yml file, and solution cover files.

        """
        solution_zip = DeployManager._copy_and_zip(catalog, catalog_local_src, active_solution, deploy_path)
        exports = DeployManager._attach_exports(catalog, catalog_local_src, active_solution, deploy_path)

        return solution_zip, exports

    @staticmethod
    def retrieve_head_name(active_solution: Solution):
        """Retrieves the branch (head) name for the merge request of the solution file."""
        coordinates = active_solution.coordinates
        return "_".join([coordinates.group, coordinates.name, coordinates.version])

    @staticmethod
    def _create_merge_request(active_solution: Solution, repo: Repo, file_paths, dry_run=False, push_option=None,
                              email=None, username=None):
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
        # make a new branch and checkout

        if push_option is None:
            push_option = []

        new_head = create_new_head(repo, DeployManager.retrieve_head_name(active_solution))
        new_head.checkout()

        commit_msg = "Adding new/updated %s" % DeployManager.retrieve_head_name(active_solution)

        add_files_commit_and_push(
            new_head,
            file_paths,
            commit_msg,
            push=not dry_run,
            push_options=push_option,
            email=email,
            username=username
        )

    @staticmethod
    def _get_absolute_zip_path(catalog: Catalog, catalog_local_src: str, active_solution: Solution):
        """ Gets the absolute path to the zip."""
        return Path(catalog_local_src).joinpath(
            catalog.get_solution_zip_suffix(
                active_solution.coordinates
            )
        )

    @staticmethod
    def _create_yaml_file_in_local_src(active_solution: Solution, solution_home: Path):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        coordinates = active_solution.coordinates

        yaml_path = solution_home.joinpath("%s%s" % (coordinates.name, ".yml"))

        module_logger().debug('Writing yaml file to: %s...' % yaml_path)
        write_dict_to_yml(yaml_path, get_deploy_dict(active_solution))

        return yaml_path

    @staticmethod
    def _create_docker_file_in_local_src(active_solution: Solution, solution_home: Path) -> Path:
        """Uses the template to create a docker file for the solution which gets deployed.

        Returns:
            The path to the docker file.
        """
        coordinates = active_solution.coordinates
        zip_name = get_zip_name(coordinates)

        docker_file = solution_home.joinpath("Dockerfile")

        docker_file_stream = pkgutil.get_data('album.docker', 'Dockerfile_solution_template.txt').decode()

        docker_file_stream = docker_file_stream.replace("<version>", album.core.__version__)
        docker_file_stream = docker_file_stream.replace("<name>", zip_name)
        docker_file_stream = docker_file_stream.replace("<run_name>", str(coordinates))
        author = "; ".join(active_solution.setup.authors) if active_solution.setup.authors else "\"\""
        docker_file_stream = docker_file_stream.replace("<maintainer>", author)

        # replace template with entries and copy dockerfile to deploy_src
        module_logger().debug('Writing docker file to: %s...' % str(docker_file))
        copy_in_file(docker_file_stream, docker_file)

        return docker_file

    @staticmethod
    def _create_changelog_file_in_local_src(active_solution: Solution, catalog: Catalog, solution_home: Path):
        """Creates a changelog file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """

        changelog_path = solution_home.joinpath("CHANGELOG.md")

        module_logger().debug('Writing changelog file to: %s...' % changelog_path)

        content = '''# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
'''
        versions = catalog.get_all_solution_versions(active_solution.coordinates.group, active_solution.coordinates.name)
        for version in versions:
            timestamp = version.setup['timestamp']
            if timestamp:
                timestamp = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')
                time = timestamp.strftime('%Y-%m-%d')
                content += '\n## [%s] - %s\n%s\n' % (version.setup['version'], time, version.setup['changelog'])

        create_path_recursively(changelog_path.parent)

        with open(changelog_path, 'w+') as yml_f:
            yml_f.write(content)

        return changelog_path

    @staticmethod
    def _copy_and_zip(catalog: Catalog, catalog_local_src: str, active_solution: Solution, folder_path):
        """Copies the deploy-file or -folder to the catalog repository.

        Returns:
            The path to the zip.

        """
        zip_path = DeployManager._get_absolute_zip_path(catalog, catalog_local_src, active_solution)
        module_logger().debug('Creating zip file in: %s...' % str(zip_path))

        if folder_path.is_dir():
            return zip_folder(folder_path, zip_path)
        if folder_path.is_file():
            tmp_dir = tempfile.TemporaryDirectory()
            tmp_solution_file = Path(tmp_dir.name).joinpath(DefaultValues.solution_default_name.value)

            copy(folder_path, tmp_solution_file)
            zip_path = zip_paths([tmp_solution_file], zip_path)

            tmp_dir.cleanup()

            return zip_path

    @staticmethod
    def _copy_cover_to_local_src(catalog: Catalog, catalog_local_src: str, active_solution: Solution, folder_path):
        """Copies all cover files to the repo.

        Returns:
            The cover list containing absolute paths of the new location.
        """
        target_path = DeployManager._get_absolute_zip_path(catalog, catalog_local_src, active_solution).parent
        cover_list = []

        if active_solution.setup.covers:
            module_logger().debug('Copying cover file to: %s...' % str(target_path))
            for cover in active_solution.setup.covers:
                cover_name = cover["source"]
                cover_path = folder_path.joinpath(cover_name)  # relative paths only
                if cover_path.exists():
                    cover_list.append(copy(cover_path, target_path.joinpath(cover_name)))
                else:
                    module_logger().warn(f"Cannot find cover {cover_path.absolute()}, proceeding without copying it...")
        return cover_list

    @staticmethod
    def _attach_exports(catalog, catalog_local_src, active_solution, deploy_path: Path):
        coordinates = active_solution.coordinates
        solution_home = Path(catalog_local_src).joinpath(Configuration.get_solution_path_suffix(coordinates))
        res = []
        res.extend(DeployManager._copy_cover_to_local_src(catalog, catalog_local_src, active_solution, deploy_path))
        res.append(DeployManager._create_docker_file_in_local_src(active_solution, solution_home))
        res.append(DeployManager._create_yaml_file_in_local_src(active_solution, solution_home))
        res.append(DeployManager._create_changelog_file_in_local_src(active_solution, catalog, solution_home))
        return res
