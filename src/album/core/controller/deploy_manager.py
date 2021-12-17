import tempfile
from datetime import datetime
from pathlib import Path

from git import Repo

from album.core.api.album import IAlbum
from album.core.api.controller.deploy_manager import IDeployManager
from album.core.api.model.catalog import ICatalog
from album.core.model.default_values import DefaultValues
from album.core.utils.export.changelog import create_changelog_file, \
    process_changelog_file
from album.core.utils.export.docker import create_docker_file
from album.core.utils.operations.dict_operations import get_dict_entries_from_attribute_path
from album.core.utils.operations.file_operations import copy, write_dict_to_yml, zip_folder, zip_paths, force_remove, \
    folder_empty
from album.core.utils.operations.git_operations import create_new_head, add_files_commit_and_push
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner import album_logging
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution

module_logger = album_logging.get_active_logger


class DeployManager(IDeployManager):

    def __init__(self, album: IAlbum):
        self.album = album

    def deploy(self, deploy_path, catalog_name: str, dry_run: bool, push_option=None, git_email: str = None,
               git_name: str = None,
               force_deploy: bool = False, changelog: str = ""):

        if dry_run:
            module_logger().info('Pretending to deploy %s to %s...' % (deploy_path, catalog_name))
        else:
            module_logger().info('Deploying %s to %s...' % (deploy_path, catalog_name))

        deploy_path = Path(deploy_path)

        if deploy_path.is_dir():
            path_to_solution = deploy_path.joinpath(DefaultValues.solution_default_name.value)
        else:
            path_to_solution = deploy_path

        active_solution = self.album.state_manager().load(path_to_solution)
        active_solution.setup().changelog = changelog

        # case catalog given
        if catalog_name:
            catalog = self.album.collection_manager().catalogs().get_by_name(catalog_name)

        # case catalog in solution file specified
        # TODO: discuss this
        elif active_solution.setup().deploy and active_solution.setup().deploy["catalog"]:
            catalog = self.album.collection_manager().catalogs().get_by_src(
                active_solution.setup().deploy["catalog"]["src"]
            )

        # case no catalog given
        else:
            raise RuntimeError("No catalog specified for deployment!")

        self.album.migration_manager().load_index(catalog)

        process_changelog_file(catalog, active_solution, deploy_path)

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

    def _deploy_to_remote_catalog(self, catalog: ICatalog, active_solution: ISolution, deploy_path, dry_run,
                                  push_option,
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

    def get_download_path(self, catalog: ICatalog):
        return Path(self.album.configuration().cache_path_download()).joinpath(catalog.name())

    def _deploy_to_local_catalog(self, catalog: ICatalog, active_solution: ISolution, deploy_path, dry_run: bool,
                                 force_deploy: bool):
        """Routine to deploy to a local catalog."""
        # check for cache catalog only
        if catalog.is_cache():
            raise RuntimeError("Cannot deploy to catalog only used for caching! Aborting...")

        # set src to catalog.src, as we know this is a (network) path, not a remote link
        catalog_local_src = catalog.src()
        active_solution.setup()["timestamp"] = datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')

        # check if catalog_local_src is empty
        catalog_local_src_solution_path = self._get_absolute_prefix_path(
            catalog, catalog_local_src, active_solution
        )
        if catalog_local_src_solution_path.exists() and not folder_empty(catalog_local_src_solution_path):
            if force_deploy:
                force_remove(catalog_local_src_solution_path)
            else:
                raise RuntimeError("The deploy target folder is not empty! Enable --force-deploy to continue!")

        # update the index
        if not dry_run:
            catalog.add(active_solution, force_overwrite=force_deploy)
        else:
            module_logger().info("Would add the solution %s to index..." % active_solution.coordinates().name())

        # include files/folders in catalog
        zip_path, export = self._deploy_routine_in_local_src(catalog, catalog_local_src, active_solution,
                                                             deploy_path)

        # copy to source
        if not dry_run:
            try:
                catalog.copy_index_from_cache_to_src()
            except Exception:
                module_logger().error("Copying index to src failed! Rolling back deployment...")
                zip_path.unlink()
                for e in export:
                    e.unlink()
                raise OSError("Deploy failed!")

            # refresh the local index of the catalog
            self.album.migration_manager().refresh_index(catalog)
        else:
            module_logger().info(
                "Would copy the index to src %s to %s..." % (catalog.index_path(), catalog.src())
            )
            module_logger().info(
                "Would refresh the index from src"
            )

    def _deploy_routine_in_local_src(self, catalog: ICatalog, catalog_local_src, active_solution, deploy_path):
        """Performs all routines a deploy process needs to do locally.

        Returns:
            solution zip file and additional attachments.

        """
        solution_zip = self._copy_and_zip(catalog_local_src, active_solution, deploy_path)
        exports = self._attach_exports(catalog, catalog_local_src, active_solution, deploy_path)

        return solution_zip, exports

    @staticmethod
    def retrieve_head_name(active_solution: ISolution):
        """Retrieves the branch (head) name for the merge request of the solution file."""
        coordinates = active_solution.coordinates()
        return "_".join([coordinates.group(), coordinates.name(), coordinates.version()])

    @staticmethod
    def _create_merge_request(active_solution: ISolution, repo: Repo, file_paths, dry_run=False, push_option=None,
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

    def _get_absolute_zip_path(self, catalog_local_src: str, active_solution: ISolution):
        """ Gets the absolute path to the zip."""
        return Path(catalog_local_src).joinpath(
            self.album.collection_manager().solutions().get_solution_zip_suffix(active_solution.coordinates())
        )

    def _get_absolute_prefix_path(self, catalog: ICatalog, catalog_local_src: str, active_solution: ISolution):
        return Path(catalog_local_src).joinpath(
            self.album.collection_manager().solutions().get_solution_path(catalog, active_solution.coordinates())
        )

    @staticmethod
    def _create_yaml_file_in_local_src(active_solution: ISolution, solution_home: Path):
        """Creates a yaml file in the given repo for the given solution.

        Returns:
            The Path to the created markdown file.

        """
        coordinates = active_solution.coordinates()

        yaml_path = solution_home.joinpath("%s%s" % (coordinates.name(), ".yml"))

        module_logger().debug('Writing yaml file to: %s...' % yaml_path)
        write_dict_to_yml(yaml_path, get_deploy_dict(active_solution))

        return yaml_path

    def _copy_and_zip(self, catalog_local_src: str, active_solution: Solution, folder_path) -> Path:
        """Copies the deploy-file or -folder to the catalog repository.

        Returns:
            The path to the zip.

        """
        zip_path = self._get_absolute_zip_path(catalog_local_src, active_solution)
        module_logger().debug('Creating zip file in: %s...' % str(zip_path))

        if folder_path.is_dir():
            zip_file = Path(zip_folder(folder_path, zip_path))
            return zip_file
        if folder_path.is_file():
            tmp_dir = tempfile.TemporaryDirectory()
            tmp_solution_file = Path(tmp_dir.name).joinpath(DefaultValues.solution_default_name.value)

            copy(folder_path, tmp_solution_file)
            zip_path = zip_paths([tmp_solution_file], zip_path)

            tmp_dir.cleanup()

            return Path(zip_path)

    @staticmethod
    def _copy_files_from_solution(
            active_solution: ISolution, source_path: Path, target_path: Path, name, attribute_path
    ):
        files = []
        source_path = Path(source_path)
        target_path = Path(target_path)
        module_logger().debug('Looking up %s file(s) to copy to %s...' % (name, str(target_path)))

        # get files in solution setup dictionary having the given attribute_path
        file_names = get_dict_entries_from_attribute_path(active_solution.setup(), attribute_path)
        module_logger().debug('Lookup result: %s' % ', '.join(file_names))

        for file_name in file_names:

            file_source_path = source_path.joinpath(file_name)  # relative paths only
            if file_source_path.exists():
                files.append(copy(file_source_path, target_path.joinpath(file_name)))
            else:
                module_logger().warn(
                    'Cannot find %s %s, proceeding without copying...' % (name, file_source_path.absolute()))
        return files

    def _attach_exports(self, catalog: ICatalog, catalog_local_src: str, active_solution: ISolution, deploy_path: Path):
        coordinates = active_solution.coordinates()

        catalog_solution_local_src_path = Path(catalog_local_src).joinpath(
            self.album.configuration().get_solution_path_suffix(coordinates)
        )

        res = []
        res.extend(DeployManager._copy_files_from_solution(
            active_solution, deploy_path, catalog_solution_local_src_path, 'cover', 'covers.source')
        )
        res.extend(DeployManager._copy_files_from_solution(
            active_solution, deploy_path, catalog_solution_local_src_path, 'documentation', 'documentation')
        )
        res.append(create_docker_file(active_solution, catalog_solution_local_src_path))
        res.append(DeployManager._create_yaml_file_in_local_src(active_solution, catalog_solution_local_src_path))
        res.append(create_changelog_file(active_solution, catalog, catalog_solution_local_src_path))

        return res
