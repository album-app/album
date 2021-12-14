from abc import ABCMeta, abstractmethod

from album.core.api.controller.clone_manager import ICloneManager
from album.core.api.controller.collection.collection_manager import ICollectionManager
from album.core.api.controller.deploy_manager import IDeployManager
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.controller.install_manager import IInstallManager
from album.core.api.controller.migration_manager import IMigrationManager
from album.core.api.controller.run_manager import IRunManager
from album.core.api.controller.search_manager import ISearchManager
from album.core.api.controller.state_manager import IStateManager
from album.core.api.controller.task_manager import ITaskManager
from album.core.api.controller.test_manager import ITestManager
from album.core.api.model.configuration import IConfiguration


class IAlbum:
    __metaclass__ = ABCMeta

    @abstractmethod
    def deploy_manager(self) -> IDeployManager: raise NotImplementedError

    @abstractmethod
    def install_manager(self) -> IInstallManager: raise NotImplementedError

    @abstractmethod
    def collection_manager(self) -> ICollectionManager: raise NotImplementedError

    @abstractmethod
    def run_manager(self) -> IRunManager: raise NotImplementedError

    @abstractmethod
    def test_manager(self) -> ITestManager: raise NotImplementedError

    @abstractmethod
    def search_manager(self) -> ISearchManager: raise NotImplementedError

    @abstractmethod
    def clone_manager(self) -> ICloneManager: raise NotImplementedError

    @abstractmethod
    def configuration(self) -> IConfiguration: raise NotImplementedError

    @abstractmethod
    def environment_manager(self) -> IEnvironmentManager: raise NotImplementedError

    @abstractmethod
    def task_manager(self) -> ITaskManager: raise NotImplementedError

    @abstractmethod
    def migration_manager(self) -> IMigrationManager: raise NotImplementedError

    @abstractmethod
    def state_manager(self) -> IStateManager: raise NotImplementedError

    @abstractmethod
    def close(self): raise NotImplementedError
