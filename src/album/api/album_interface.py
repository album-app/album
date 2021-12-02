from abc import ABCMeta, abstractmethod

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


class AlbumInterface:
    __metaclass__ = ABCMeta

    @abstractmethod
    def deploy_manager(self) -> DeployInterface: raise NotImplementedError

    @abstractmethod
    def install_manager(self) -> InstallInterface: raise NotImplementedError

    @abstractmethod
    def collection_manager(self) -> CollectionInterface: raise NotImplementedError

    @abstractmethod
    def run_manager(self) -> RunInterface: raise NotImplementedError

    @abstractmethod
    def test_manager(self) -> TestInterface: raise NotImplementedError

    @abstractmethod
    def search_manager(self) -> SearchInterface: raise NotImplementedError

    @abstractmethod
    def clone_manager(self) -> CloneInterface: raise NotImplementedError

    @abstractmethod
    def configuration(self) -> ConfigurationInterface: raise NotImplementedError

    @abstractmethod
    def environment_manager(self) -> EnvironmentInterface: raise NotImplementedError

    @abstractmethod
    def task_manager(self) -> TaskInterface: raise NotImplementedError

    @abstractmethod
    def migration_manager(self) -> MigrationInterface: raise NotImplementedError

    @abstractmethod
    def state_manager(self) -> StateInterface: raise NotImplementedError

    @abstractmethod
    def close(self): raise NotImplementedError
