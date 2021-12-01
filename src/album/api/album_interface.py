from abc import ABCMeta, abstractmethod

from album.api.state_interface import StateInterface
from album.api.clone_interface import CloneInterface
from album.api.collection.collection_interface import CollectionInterface
from album.api.config_interface import ConfigurationInterface
from album.api.deploy_interface import DeployInterface
from album.api.environment_interface import EnvironmentInterface
from album.api.install_interface import InstallInterface
from album.api.migration_interface import MigrationInterface
from album.api.run_interface import RunInterface
from album.api.search_interface import SearchInterface
from album.api.task_interface import TaskInterface
from album.api.test_interface import TestInterface


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
