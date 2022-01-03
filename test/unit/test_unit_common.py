import gc
import logging
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

from album.api import Album
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.runner import album_logging
from album.runner.album_logging import pop_active_logger, LogLevel, configure_logging
from test.global_exception_watcher import GlobalExceptionWatcher


class TestUnitCommon(unittest.TestCase):
    """Base class for all Unittest using a album object"""

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.captured_output = StringIO()
        self.configure_test_logging(self.captured_output)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()
        self.album: Optional[Album] = None

    def tearDown(self) -> None:
        self.captured_output.close()

        while True:
            logger = pop_active_logger()
            if logger == logging.getLogger():
                break

        Path(self.closed_tmp_file.name).unlink()
        if self.album:
            self.album.close()
        album_logging._active_logger = {}
        gc.collect()
        try:
            self.tmp_dir.cleanup()
        except PermissionError:
            try:
                force_remove(self.tmp_dir.name)
            except PermissionError:
                raise

    def run(self, result=None):
        # add watcher to catch any exceptions thrown in threads
        with GlobalExceptionWatcher():
            super(TestUnitCommon, self).run(result)

    def configure_test_logging(self, stream_handler):
        self.logger = configure_logging("unitTest", loglevel=LogLevel.INFO)
        ch = logging.StreamHandler(stream_handler)
        ch.setLevel('INFO')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def get_logs(self):
        logs = self.logger.handlers[0].stream.getvalue()
        logs = logs.strip()
        return logs.split("\n")

    def create_album_test_instance(self, init_collection=True, init_catalogs=True) -> Album:
        self.album = Album(base_cache_path=Path(self.tmp_dir.name).joinpath("album"))

        if init_catalogs:
            catalogs_dict = {
                    DefaultValues.local_catalog_name.value:
                        Path(self.tmp_dir.name).joinpath("album", DefaultValues.catalog_folder_prefix.value,
                                                         DefaultValues.local_catalog_name.value)
                }
            # mock retrieve_catalog_meta_information as it involves a http request
            with patch("album.core.controller.collection.catalog_handler.CatalogHandler._retrieve_catalog_meta_information") as retrieve_c_m_i_mock:
                get_initial_catalogs_mock = MagicMock(
                    return_value=catalogs_dict
                )
                self.album.configuration().get_initial_catalogs = get_initial_catalogs_mock
                retrieve_c_m_i_mock.side_effect = [
                    {"name": "catalog_local", "version": "0.1.0"},  # local catalog creation call
                    {"name": "catalog_local", "version": "0.1.0"},  # local catalog load_index call
                ]
                # create collection
                self.album._controller.collection_manager().load_or_create()
        elif init_collection:
            # mock retrieve_catalog_meta_information as it involves a http request
            with patch("album.core.controller.collection.catalog_handler.CatalogHandler.add_initial_catalogs"):
                self.album._controller.collection_manager().load_or_create()

        return self.album
