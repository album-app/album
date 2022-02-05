import pathlib
from typing import Optional, Union

from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.configuration import IConfiguration
from album.core.controller.album_controller import AlbumController
from album.core.utils.core_logging import configure_root_logger
from album.runner.album_logging import pop_active_logger, LogLevel
from album.runner.core.api.model.script_creator import IScriptCreator
from album.runner.core.api.model.solution import ISolution


class Album:
    class Builder:
        _base_cache_path: Optional[Union[str, pathlib.Path]] = None
        _log_format: str = None
        _log_format_time: str = None
        _log_level: LogLevel = None

        def base_cache_path(self, base_cache_path: Union[str, pathlib.Path]) -> 'Album.Builder':
            self._base_cache_path = base_cache_path
            return self

        def log_format(self, log_format: str) -> 'Album.Builder':
            self._log_format = log_format
            return self

        def log_format_time(self, log_format_time: str) -> 'Album.Builder':
            self._log_format_time = log_format_time
            return self

        def log_level(self, log_level: LogLevel) -> 'Album.Builder':
            self._log_level = log_level
            return self

        def build(self) -> 'Album':
            return Album(self)

    def __init__(self, builder: 'Album.Builder') -> None:
        self._options = builder
        self._controller = AlbumController(self._options._base_cache_path)
        self.logger_pushed = True
        configure_root_logger(log_format=self._options._log_format, log_format_time=self._options._log_format_time,
                              log_level=self._options._log_level)

    def resolve(self, resolve_solution: str) -> ICollectionSolution:
        return self._controller.collection_manager().resolve_and_load(resolve_solution)

    def resolve_installed(self, resolve_solution: str) -> ICollectionSolution:
        return self._controller.collection_manager().resolve_installed_and_load(resolve_solution)

    def load_or_create_collection(self):
        self._controller.collection_manager().load_or_create()

    def get_index_as_dict(self):
        return self._controller.collection_manager().get_index_as_dict()

    def get_catalogs_as_dict(self):
        return self._controller.collection_manager().catalogs().get_all_as_dict()

    def get_catalog_by_name(self, name) -> ICatalog:
        return self._controller.catalogs().get_by_name(name)

    def get_catalog_by_src(self, src) -> ICatalog:
        return self._controller.catalogs().get_by_src(src)

    def get_collection_index(self) -> ICollectionIndex:
        return self._controller.collection_manager().get_collection_index()

    def test(self, collection_solution: ICollectionSolution, args=None):
        return self._controller.test_manager().test(collection_solution, args)

    def load(self, path) -> Optional[ISolution]:
        return self._controller.state_manager().load(path)

    def search(self, keywords):
        """Searches through album catalogs to find closest matching solution.
        """
        return self._controller.search_manager().search(keywords)

    def run(self, collection_solution: ICollectionSolution, argv=None, run_immediately=False):
        return self._controller.run_manager().run(collection_solution, run_immediately, argv)

    def install(self, collection_solution: ICollectionSolution, argv=None):
        return self._controller.install_manager().install(collection_solution, argv)

    def uninstall(self, collection_solution: ICollectionSolution, rm_dep=False, argv=None):
        """Removes a solution from the disk. Thereby uninstalling its environment and deleting all its downloads.

        Args:
            argv:
                Arguments which should be appended to the script call
            collection_solution:
                The solution to remove
            rm_dep:
                Boolean to indicate whether to remove parents too.

        """
        return self._controller.install_manager().uninstall(collection_solution, rm_dep, argv)

    def deploy(self, deploy_path: str, catalog_name: str, dry_run: bool, push_option=None, git_email: str = None,
               git_name: str = None, force_deploy: bool = False, changelog: str = ""):
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
            changelog:
                The change associated with this version of a solution compared to the last version.

        """
        return self._controller.deploy_manager().deploy(deploy_path=deploy_path, catalog_name=catalog_name, dry_run=dry_run,
                                                        push_options=push_option, git_email=git_email, git_name=git_name,
                                                        force_deploy=force_deploy, changelog=changelog)

    def clone(self, path: str, target_dir: str, name: str) -> None:
        """
        Function corresponding to the `clone` subcommand of `album`.

        Args:
            path: the source of the clone command - a solution (group:name:version, path, or URL to file) or a catalog
                template string (i.e. template:catalog)
            target_dir: the directory where the cloned solution or catalog will be added to
            name: the name of the solution or catalog to be created

        """
        return self._controller.clone_manager().clone(path, target_dir, name)

    def close(self):
        if self.logger_pushed:
            pop_active_logger()
        self._controller.close()

    def run_solution_script(self, resolve_result: ICollectionSolution, script: IScriptCreator):
        self._controller.script_manager().run_solution_script(resolve_result, script)

    def upgrade(self, catalog_name=None, dry_run=False):
        return self._controller.collection_manager().catalogs().update_collection(catalog_name, dry_run)

    def update(self, catalog_name=None):
        return self._controller.collection_manager().catalogs().update_any(catalog_name)

    def add_catalog(self, catalog_src):
        return self._controller.collection_manager().catalogs().add_by_src(catalog_src)

    def remove_catalog_by_src(self, catalog_src):
        return self._controller.collection_manager().catalogs().remove_from_collection_by_src(catalog_src)

    def remove_catalog_by_name(self, catalog_src):
        return self._controller.collection_manager().catalogs().remove_from_collection_by_name(catalog_src)

    def configuration(self) -> IConfiguration:
        return self._controller.configuration()

    def is_installed(self, resolve_result: ICollectionSolution):
        return self._controller.solutions().is_installed(resolve_result.catalog(), resolve_result.coordinates())

    def load_catalog_index(self, catalog: ICatalog):
        return self._controller.migration_manager().load_index(catalog)