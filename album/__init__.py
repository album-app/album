from album.core.model.configuration import Configuration

from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.test_manager import TestManager
from album.core.server import AlbumServer


__version__ = "0.1.0"
__author__ = "Kyle Harrington, Jan Philipp Albrecht, Deborah Schmidt"
__email__ = "album@kyleharrington.com"


class Album:

    @staticmethod
    def collection_manager():
        return CollectionManager()

    @staticmethod
    def deploy_manager():
        return DeployManager()

    @staticmethod
    def install_manager():
        return InstallManager()

    @staticmethod
    def run_manager():
        return RunManager()

    @staticmethod
    def test_manager():
        return TestManager()

    @staticmethod
    def search_manager():
        return SearchManager()

    @staticmethod
    def clone_manager():
        return CloneManager()

    @staticmethod
    def start_server(port, host):
        AlbumServer(port, host).start()

    @staticmethod
    def configuration():
        return Configuration()
