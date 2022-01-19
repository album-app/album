from pathlib import Path
from typing import Optional

from album.api import Album
from album.core.api.controller.collection.collection_manager import ICollectionManager
from test.global_exception_watcher import GlobalExceptionWatcher
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestUnitCommon(TestUnitCoreCommon):
    """Base class for all Unittest using a album object"""

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.configure_test_logging()
        self._setup_tmp_resources()
        self.album: Optional[Album] = None

    def collection_manager(self) -> Optional[ICollectionManager]:
        if self.album:
            return self.album._controller.collection_manager()
        return None

    def tearDown(self) -> None:
        if self.album:
            self.album.close()
        super().tearDown()

    def run(self, result=None):
        # add watcher to catch any exceptions thrown in threads
        with GlobalExceptionWatcher():
            super(TestUnitCommon, self).run(result)

    def create_album_test_instance(self, init_collection=True, init_catalogs=True) -> Album:
        self.album = Album.Builder().base_cache_path(Path(self.tmp_dir.name).joinpath("album")).build()
        self.configure_test_logging()
        self._setup_collection(init_catalogs, init_collection)
        return self.album
