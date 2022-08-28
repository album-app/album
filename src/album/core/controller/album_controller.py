from pathlib import Path
from typing import Optional

from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.controller.controller import IAlbumController
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.controller.event_manager import IEventManager
from album.core.api.controller.migration_manager import IMigrationManager
from album.core.api.controller.script_manager import IScriptManager
from album.core.api.controller.task_manager import ITaskManager
from album.core.api.model.configuration import IConfiguration
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.environment_manager import EnvironmentManager
from album.core.controller.event_manager import EventManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.migration_manager import MigrationManager
from album.core.controller.run_manager import RunManager
from album.core.controller.script_manager import ScriptManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.state_manager import StateManager
from album.core.controller.task_manager import TaskManager
from album.core.controller.test_manager import TestManager
from album.core.model.configuration import Configuration


class AlbumController(IAlbumController):
    def __init__(self, base_cache_path: Optional[Path] = None) -> None:
        self.base_cache_path = base_cache_path
        self._deploy_manager = None
        self._run_manager = None
        self._install_manager = None
        self._collection_manager: Optional[CollectionManager] = None
        self._test_manager = None
        self._migration_manager = None
        self._search_manager = None
        self._clone_manager = None
        self._environment_manager = None
        self._state_manager = None
        self._script_manager = None
        self._event_manager = None
        self._task_manager = None
        self._configuration = None

    def catalogs(self) -> ICatalogHandler:
        return self.collection_manager().catalogs()

    def solutions(self) -> ISolutionHandler:
        return self.collection_manager().solutions()

    def configuration(self) -> IConfiguration:
        if not self._configuration:
            self._configuration = Configuration()
            self._configuration.setup(base_cache_path=self.base_cache_path)
        return self._configuration

    def environment_manager(self) -> IEnvironmentManager:
        if not self._environment_manager:
            self._environment_manager = EnvironmentManager(self)
        return self._environment_manager

    def migration_manager(self) -> IMigrationManager:
        if not self._migration_manager:
            self._migration_manager = MigrationManager(self)
        return self._migration_manager

    def script_manager(self) -> IScriptManager:
        if not self._script_manager:
            self._script_manager = ScriptManager(self)
        return self._script_manager

    def deploy_manager(self) -> DeployManager:
        if not self._deploy_manager:
            self._deploy_manager = DeployManager(self)
        return self._deploy_manager

    def install_manager(self) -> InstallManager:
        if not self._install_manager:
            self._install_manager = InstallManager(self)
        return self._install_manager

    def run_manager(self) -> RunManager:
        if not self._run_manager:
            self._run_manager = RunManager(self)
        return self._run_manager

    def test_manager(self) -> TestManager:
        if not self._test_manager:
            self._test_manager = TestManager(self)
        return self._test_manager

    def search_manager(self) -> SearchManager:
        if not self._search_manager:
            self._search_manager = SearchManager(self)
        return self._search_manager

    def clone_manager(self) -> CloneManager:
        if not self._clone_manager:
            self._clone_manager = CloneManager(self)
        return self._clone_manager

    def state_manager(self) -> StateManager:
        if not self._state_manager:
            self._state_manager = StateManager(self)
        return self._state_manager

    def collection_manager(self) -> CollectionManager:
        if not self._collection_manager:
            self._collection_manager = CollectionManager(self)
        return self._collection_manager

    def event_manager(self) -> IEventManager:
        if not self._event_manager:
            self._event_manager = EventManager()
        return self._event_manager

    def task_manager(self) -> ITaskManager:
        if not self._task_manager:
            self._task_manager = TaskManager()
        return self._task_manager

    def close(self):
        if self._collection_manager:
            self._collection_manager.close()
