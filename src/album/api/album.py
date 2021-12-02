from pathlib import Path
from typing import Optional

from album.api.album_interface import AlbumInterface
from album.api.controller.clone_interface import CloneInterface
from album.api.controller.collection.collection_interface import CollectionInterface
from album.api.controller.config_interface import ConfigurationInterface
from album.api.controller.deploy_interface import DeployInterface
from album.api.controller.environment_interface import EnvironmentInterface
from album.api.controller.install_interface import InstallInterface
from album.api.controller.migration_interface import MigrationInterface
from album.api.controller.run_interface import RunInterface
from album.api.controller.search_interface import SearchInterface
from album.api.controller.state_interface import StateInterface
from album.api.controller.task_interface import TaskInterface
from album.api.controller.test_interface import TestInterface
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.environment_manager import EnvironmentManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.migration_manager import MigrationManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.state_manager import StateManager
from album.core.controller.task_manager import TaskManager
from album.core.controller.test_manager import TestManager
from album.core.model.configuration import Configuration


class Album(AlbumInterface):

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
        self._task_manager = None
        self._state_manager = None
        self._configuration = None

    def collection_manager(self) -> CollectionInterface:
        if not self._collection_manager:
            self._collection_manager = CollectionManager(self)
        return self._collection_manager

    def deploy_manager(self) -> DeployInterface:
        if not self._deploy_manager:
            self._deploy_manager = DeployManager(self)
        return self._deploy_manager

    def install_manager(self) -> InstallInterface:
        if not self._install_manager:
            self._install_manager = InstallManager(self)
        return self._install_manager

    def run_manager(self) -> RunInterface:
        if not self._run_manager:
            self._run_manager = RunManager(self)
        return self._run_manager

    def test_manager(self) -> TestInterface:
        if not self._test_manager:
            self._test_manager = TestManager(self)
        return self._test_manager

    def search_manager(self) -> SearchInterface:
        if not self._search_manager:
            self._search_manager = SearchManager(self)
        return self._search_manager

    def clone_manager(self) -> CloneInterface:
        if not self._clone_manager:
            self._clone_manager = CloneManager(self)
        return self._clone_manager

    def configuration(self) -> ConfigurationInterface:
        if not self._configuration:
            self._configuration = Configuration()
            self._configuration.setup(base_cache_path=self.base_cache_path)
        return self._configuration

    def environment_manager(self) -> EnvironmentInterface:
        if not self._environment_manager:
            self._environment_manager = EnvironmentManager(self)
        return self._environment_manager

    def task_manager(self) -> TaskInterface:
        if not self._task_manager:
            self._task_manager = TaskManager()
        return self._task_manager

    def migration_manager(self) -> MigrationInterface:
        if not self._migration_manager:
            self._migration_manager = MigrationManager(self)
        return self._migration_manager

    def state_manager(self) -> StateInterface:
        if not self._state_manager:
            self._state_manager = StateManager(self)
        return self._state_manager

    def close(self):
        if self._collection_manager:
            self._collection_manager.close()
