import pathlib
from typing import Optional, Union

from album.core.api.controller.controller import IAlbumController
from album.core.api.model.catalog import ICatalog
from album.core.api.model.collection_index import ICollectionIndex
from album.core.api.model.collection_solution import ICollectionSolution
from album.core.api.model.configuration import IConfiguration
from album.core.api.model.event import IEvent
from album.core.api.model.task import ITask
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

        def base_cache_path(
            self, base_cache_path: Union[str, pathlib.Path]
        ) -> "Album.Builder":
            self._base_cache_path = base_cache_path
            return self

        def log_format(self, log_format: str) -> "Album.Builder":
            self._log_format = log_format
            return self

        def log_format_time(self, log_format_time: str) -> "Album.Builder":
            self._log_format_time = log_format_time
            return self

        def log_level(self, log_level: LogLevel) -> "Album.Builder":
            self._log_level = log_level
            return self

        def build(self) -> "Album":
            _controller = AlbumController(self._base_cache_path)
            configure_root_logger(
                log_format=self._log_format,
                log_format_time=self._log_format_time,
                log_level=self._log_level,
            )
            return Album(_controller, logger_pushed=True)

    def __init__(self, album_controller: IAlbumController, logger_pushed=False) -> None:
        self._controller = album_controller
        self.logger_pushed = logger_pushed

    def __del__(self):
        self.close()

    def resolve(self, resolve_solution: str) -> ICollectionSolution:
        return self._controller.collection_manager().resolve_and_load(resolve_solution)

    def resolve_installed(self, resolve_solution: str) -> ICollectionSolution:
        return self._controller.collection_manager().resolve_installed_and_load(
            resolve_solution
        )

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

    def test(self, solution_to_resolve: str, args=None):
        return self._controller.test_manager().test(solution_to_resolve, args)

    def load(self, path) -> Optional[ISolution]:
        return self._controller.state_manager().load(path)

    def search(self, keywords):
        """Searches through album catalogs to find closest matching solution."""
        return self._controller.search_manager().search(keywords)

    def run(self, solution_to_resolve: str, argv=None, run_async=False):
        return self._run_async(
            self._controller.run_manager().run,
            (solution_to_resolve, False, argv),
            run_async,
        )

    def install(self, solution_to_resolve: str, argv=None, run_async=False):
        return self._run_async(
            self._controller.install_manager().install,
            (solution_to_resolve, argv),
            run_async,
        )

    def uninstall(
        self, solution_to_resolve: str, rm_dep=False, argv=None, run_async=False
    ):
        """Removes a solution from the disk. Thereby uninstalling its environment and deleting all its downloads.

        Args:
            argv:
                Arguments which should be appended to the script call
            solution_to_resolve:
                The solution to remove
            rm_dep:
                Boolean to indicate whether to remove parents too.

        """
        return self._run_async(
            self._controller.install_manager().uninstall,
            (solution_to_resolve, rm_dep, argv),
            run_async,
        )

    def deploy(
        self,
        deploy_path: str,
        catalog_name: str,
        dry_run: bool,
        push_options=None,
        git_email: str = None,
        git_name: str = None,
        force_deploy: bool = False,
        changelog: str = "",
    ):
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
            push_options:
                Push options for the catalog repository.
            git_email:
                The git email to use. (Default: systems git configuration)
            git_name:
                The git user to use. (Default: systems git configuration)
            changelog:
                The change associated with this version of a solution compared to the last version.

        """
        return self._controller.deploy_manager().deploy(
            deploy_path=deploy_path,
            catalog_name=catalog_name,
            dry_run=dry_run,
            push_options=push_options,
            git_email=git_email,
            git_name=git_name,
            force_deploy=force_deploy,
            changelog=changelog,
        )

    def undeploy(
        self,
        solution_to_resolve: str,
        catalog_name: str,
        dry_run: bool,
        push_options=None,
        git_email: str = None,
        git_name: str = None,
    ):
        """Function corresponding to the `undeploy` subcommand of `album`.

        Removes the solution from the given catalog.

        Args:
            solution_to_resolve:
                Solution identifier which should be removed (group:name:version).
            catalog_name:
                The catalog to remove the solution from.
            dry_run:
                When set, prepares undeploy in local src of the catalog,
                but not actually removing it the catalog src.
            push_options:
                Push options for the catalog repository.
            git_email:
                The git email to use. (Default: systems git configuration)
            git_name:
                The git user to use. (Default: systems git configuration)

        """
        return self._controller.deploy_manager().undeploy(
            solution_to_resolve=solution_to_resolve,
            catalog_name=catalog_name,
            dry_run=dry_run,
            push_options=push_options,
            git_email=git_email,
            git_name=git_name,
        )

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

    def run_solution_script(
        self, resolve_result: ICollectionSolution, script: IScriptCreator
    ):
        self._controller.script_manager().run_solution_script(resolve_result, script)

    def upgrade(self, catalog_name=None, dry_run=False, override=False):
        return (
            self._controller.collection_manager()
            .catalogs()
            .update_collection(catalog_name, dry_run, override)
        )

    def update(self, catalog_name=None):
        return self._controller.collection_manager().catalogs().update_any(catalog_name)

    def add_catalog(self, catalog_src):
        return self._controller.collection_manager().catalogs().add_by_src(catalog_src)

    def remove_catalog_by_src(self, catalog_src):
        return (
            self._controller.collection_manager()
            .catalogs()
            .remove_from_collection_by_src(catalog_src)
        )

    def remove_catalog_by_name(self, catalog_src):
        return (
            self._controller.collection_manager()
            .catalogs()
            .remove_from_collection_by_name(catalog_src)
        )

    def configuration(self) -> IConfiguration:
        return self._controller.configuration()

    def is_installed(self, solution_to_resolve: str):
        resolve_result = self.resolve(solution_to_resolve)
        return self._controller.solutions().is_installed(
            resolve_result.catalog(), resolve_result.coordinates()
        )

    def load_catalog_index(self, catalog: ICatalog):
        return self._controller.migration_manager().load_index(catalog)

    def add_event_listener(self, event_name, callback, solution_id=None):
        return self._controller.event_manager().add_listener(
            event_name, callback, solution_id
        )

    def remove_event_listener(self, event_name, callback, solution_id=None):
        return self._controller.event_manager().remove_listener(
            event_name, callback, solution_id
        )

    def publish_event(self, event: IEvent):
        return self._controller.event_manager().publish(event)

    def get_task_status(self, task_id) -> ITask.Status:
        """Get the status of a task managed by the task manager."""
        task = self._controller.task_manager().get_task(task_id)
        if task is None:
            raise LookupError("Task with id %s not found." % task_id)
        return self._controller.task_manager().get_status(task)

    def create_and_register_task(self, method, args) -> str:
        return self._controller.task_manager().create_and_register_task(method, args)

    def finish_tasks(self):
        return self._controller.task_manager().finish_tasks()

    def _run_async(self, method, args, run_async=False):
        if run_async:
            return self._controller.task_manager().create_and_register_task(
                method, args
            )
        else:
            return method(*args)
