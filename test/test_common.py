import gc
import logging
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from test.global_exception_watcher import GlobalExceptionWatcher
from typing import Optional
from unittest.mock import patch

from album.api import Album
from album.core.controller.album_controller import AlbumController
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.git_operations import (
    add_files_commit_and_push,
    clone_repository,
    create_bare_repository,
)
from album.core.utils.operations.view_operations import (
    get_logger_name_minimizer_filter,
    get_logging_formatter,
    get_message_filter,
)
from album.runner.album_logging import get_active_logger


class TestCommon(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.setup_tmp_resources()
        self.setup_silent_test_logging()
        self.enable_test_logging()
        self.album: Optional[Album] = None
        self.album_controller: Optional[AlbumController] = None

    def enable_test_logging(self):
        if os.getenv("ALBUM_TEST_LOGGING", "False") == "True":
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel("DEBUG")
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel("DEBUG")
            self.logger.debug("Test logging enabled!")

    def tearDown(self) -> None:
        if self.album:
            self.album.close()
            self.album_patch.stop()
        self.logger.handlers.clear()
        self.teardown_tmp_resources()
        super().tearDown()

    def setup_tmp_resources(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

    def setup_album_controller(self):
        if self.album_controller:
            raise AttributeError(
                "Only one instance of an AlbumController should be used!"
                "Either use setup_album_instance or setup_album_controller!"
            )
        self.album_controller = AlbumController(base_cache_path=Path(self.tmp_dir.name))

    def setup_album_instance(self):
        if self.album:
            raise AttributeError(
                "Only one instance of an Album should be used!"
                "Either use setup_album_instance or setup_album_controller!"
            )
        with patch("album.api.configure_root_logger"):
            self.album = (
                Album.Builder().base_cache_path(Path(self.tmp_dir.name)).build()
            )
        if self.album_controller:
            self.album._controller = self.album_controller
        else:
            self.album_controller = self.album._controller
        self.album_patch = patch(
            "album.argument_parsing.create_album_instance", return_value=self.album
        )
        self.album_patch.start()

    def setup_silent_test_logging(self, logger_name="test-logger"):
        self.captured_output = StringIO()
        self.logger = get_active_logger()
        self.logger.handlers.clear()
        self.logger.name = logger_name
        self.logger.setLevel("INFO")
        ch = logging.StreamHandler(self.captured_output)
        ch.setLevel("INFO")
        ch.setFormatter(
            get_logging_formatter(
                fmt="%(log_color)s%(asctime)s %(levelname)s %(shortened_name)s%(message)s"
            )
        )
        ch.addFilter(get_logger_name_minimizer_filter())
        ch.addFilter(get_message_filter())
        self.logger.addHandler(ch)
        return self.logger

    def setup_empty_catalog(self, name, catalog_type="direct"):
        catalog_src_path = Path(self.tmp_dir.name).joinpath("my-catalogs", name)
        create_bare_repository(catalog_src_path)

        catalog_clone_path = Path(self.tmp_dir.name).joinpath("my-catalogs-clone", name)

        with clone_repository(catalog_src_path, catalog_clone_path) as repo:
            head = repo.active_branch

            self.album_controller.catalogs().create_new_metadata(
                catalog_clone_path, name, catalog_type
            )

            add_files_commit_and_push(
                head,
                [catalog_clone_path],
                "init",
                push=True,
                username=DefaultValues.catalog_git_user.value,
                email=DefaultValues.catalog_git_email.value,
            )

        return catalog_src_path, catalog_clone_path

    def setup_collection(self, init_catalogs=True, init_collection=True):
        if init_catalogs:
            with patch(
                "album.core.model.configuration.Configuration.get_initial_catalogs"
            ) as get_initial_catalogs_mock:
                get_initial_catalogs_mock.return_value = {}

                # create collection
                self.album_controller.collection_manager().load_or_create()
        elif init_collection:
            with patch(
                "album.core.controller.collection.catalog_handler.CatalogHandler.add_initial_catalogs"
            ):
                self.album_controller.collection_manager().load_or_create()
        # check everything is freshly initialized
        self.assertTrue(
            self.album_controller.collection_manager().get_collection_index().is_empty()
        )

    def teardown_tmp_resources(self):
        # garbage collector
        gc.collect()
        try:
            Path(self.closed_tmp_file.name).unlink()
            self.tmp_dir.cleanup()
        except (PermissionError, NotADirectoryError):
            try:
                force_remove(self.tmp_dir.name)
            except (PermissionError, NotADirectoryError):
                if sys.platform == "win32" or sys.platform == "cygwin":
                    get_active_logger().warning(
                        "Could not remove tmp dir! Cleanup failed!!"
                    )
                else:
                    raise

    def teardown_logging(self):
        self.logger.handlers.clear()
        if self.album:
            album_logger = logging.getLogger("album")
            album_logger.handlers.clear()

    def get_logs(self):
        logs = self.captured_output.getvalue()
        logs = logs.strip()
        logs = logs.split("\n")
        # remove empty strings
        logs = [log for log in logs if log]
        return self._remove_color_codes(logs)

    def get_logs_as_string(self):
        return "\n".join(self.get_logs())

    def _remove_color_codes(self, logs):
        logs = [log.replace("\x1b[0m", "") for log in logs]
        logs = [log.replace("\x1b[31m", "") for log in logs]
        logs = [log.replace("\x1b[32m", "") for log in logs]
        logs = [log.replace("\x1b[33m", "") for log in logs]

        return logs

    def run(self, result=None):
        # add watcher to catch any exceptions thrown in threads
        with GlobalExceptionWatcher():
            super().run(result)

    @staticmethod
    def get_catalog_meta_dict(
        name="cache_catalog", version="0.1.0", catalog_type="direct"
    ):
        return {"name": name, "version": version, "type": catalog_type}
