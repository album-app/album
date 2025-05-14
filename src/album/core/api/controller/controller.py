"""Interface for the Album Controller."""
from abc import ABCMeta, abstractmethod

from album.core.api.controller.clone_manager import ICloneManager
from album.core.api.controller.collection.catalog_handler import ICatalogHandler
from album.core.api.controller.collection.collection_manager import ICollectionManager
from album.core.api.controller.collection.solution_handler import ISolutionHandler
from album.core.api.controller.deploy_manager import IDeployManager
from album.core.api.controller.environment_manager import IEnvironmentManager
from album.core.api.controller.event_manager import IEventManager
from album.core.api.controller.install_manager import IInstallManager
from album.core.api.controller.migration_manager import IMigrationManager
from album.core.api.controller.resource_manager import IResourceManager
from album.core.api.controller.run_manager import IRunManager
from album.core.api.controller.script_manager import IScriptManager
from album.core.api.controller.search_manager import ISearchManager
from album.core.api.controller.shared_downloads_manager import IDownloadManager
from album.core.api.controller.state_manager import IStateManager
from album.core.api.controller.task_manager import ITaskManager
from album.core.api.controller.test_manager import ITestManager
from album.core.api.model.configuration import IConfiguration


class IAlbumController:
    """Interface for the Album Controller."""

    __metaclass__ = ABCMeta

    def catalogs(self) -> ICatalogHandler:
        """Return the catalog handler."""
        raise NotImplementedError

    @abstractmethod
    def solutions(self) -> ISolutionHandler:
        """Return the solution handler."""
        raise NotImplementedError

    @abstractmethod
    def configuration(self) -> IConfiguration:
        """Return the configuration."""
        raise NotImplementedError

    @abstractmethod
    def environment_manager(self) -> IEnvironmentManager:
        """Return the environment manager."""
        raise NotImplementedError

    @abstractmethod
    def migration_manager(self) -> IMigrationManager:
        """Return the migration manager."""
        raise NotImplementedError

    @abstractmethod
    def script_manager(self) -> IScriptManager:
        """Return the script manager."""
        raise NotImplementedError

    @abstractmethod
    def deploy_manager(self) -> IDeployManager:
        """Return the deploy manager."""
        raise NotImplementedError

    @abstractmethod
    def install_manager(self) -> IInstallManager:
        """Return the install manager."""
        raise NotImplementedError

    @abstractmethod
    def run_manager(self) -> IRunManager:
        """Return the run manager."""
        raise NotImplementedError

    @abstractmethod
    def test_manager(self) -> ITestManager:
        """Return the test manager."""
        raise NotImplementedError

    @abstractmethod
    def search_manager(self) -> ISearchManager:
        """Return the search manager."""
        raise NotImplementedError

    @abstractmethod
    def clone_manager(self) -> ICloneManager:
        """Return the clone manager."""
        raise NotImplementedError

    @abstractmethod
    def state_manager(self) -> IStateManager:
        """Return the state manager."""
        raise NotImplementedError

    @abstractmethod
    def collection_manager(self) -> ICollectionManager:
        """Return the collection manager."""
        raise NotImplementedError

    @abstractmethod
    def event_manager(self) -> IEventManager:
        """Return the event manager."""
        raise NotImplementedError

    @abstractmethod
    def task_manager(self) -> ITaskManager:
        """Return the task manager."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close the controller."""
        raise NotImplementedError

    @abstractmethod
    def resource_manager(self) -> IResourceManager:
        """Return the resource manager."""
        raise NotImplementedError

    @abstractmethod
    def download_manager(self) -> IDownloadManager:
        """Return the download manager."""
        raise NotImplementedError
