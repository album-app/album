from pathlib import Path
from typing import Optional

from album.core.concept.singleton import Singleton

from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.model.configuration import Configuration

__version__ = "0.1.0"
__author__ = "Kyle Harrington, Jan Philipp Albrecht, Deborah Schmidt"
__email__ = "album@kyleharrington.com"


class Album(metaclass=Singleton):

    def __init__(self, base_cache_path: Optional[Path] = None, configuration_file_path: Optional[Path] = None) -> None:
        Configuration().setup(base_cache_path=base_cache_path, configuration_file_path=configuration_file_path)

    @staticmethod
    def collection_manager() -> CollectionManager:
        return CollectionManager()

    @staticmethod
    def deploy_manager() -> DeployManager:
        return DeployManager()

    @staticmethod
    def install_manager() -> InstallManager:
        return InstallManager()

    @staticmethod
    def run_manager() -> RunManager:
        return RunManager()

    @staticmethod
    def test_manager() -> TestManager:
        return TestManager()

    @staticmethod
    def search_manager() -> SearchManager:
        return SearchManager()

    @staticmethod
    def clone_manager() -> CloneManager:
        return CloneManager()

    @staticmethod
    def configuration() -> Configuration:
        return Configuration()
