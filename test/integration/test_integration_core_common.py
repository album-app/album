import logging
import os
import sys
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from album.core.api.model.catalog import ICatalog
from album.core.controller.album_controller import AlbumController
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.model.default_values import DefaultValues
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import copy, force_remove
from album.runner import album_logging
from album.runner.album_logging import configure_logging, LogLevel
from album.runner.core.model.solution import Solution
from test.global_exception_watcher import GlobalExceptionWatcher


class TestIntegrationCoreCommon(unittest.TestCase):

    def setUp(self):
        # tempfile/dirs
        self.tmp_dir = tempfile.TemporaryDirectory()

        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

        # logging
        self.captured_output = StringIO()
        self.configure_silent_test_logging(self.captured_output)

        # load gateway with test configuration
        self.album_instance = AlbumController(base_cache_path=self.tmp_dir.name)
        self.collection_manager = self.album_instance.collection_manager()
        self.collection_manager.load_or_create()
        self.test_collection = self.collection_manager.get_collection_index()
        self.assertFalse(self.test_collection.is_empty())
        self.create_album_instance_patch = patch('album.argument_parsing.create_album_instance', return_value = self.album_instance)
        self.create_album_instance_patch.start()

    def get_album(self):
        return self.album_instance

    def add_test_catalog(self) -> ICatalog:
        path = Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog")
        CatalogHandler.create_new_catalog(path, "test_catalog")
        return self.collection_manager.catalogs().add_by_src(path)

    def tearDown(self) -> None:
        # clean all environments specified in test-resources
        self.create_album_instance_patch.stop()
        local_catalog_name = str(self.collection_manager.catalogs().get_local_catalog().name())
        env_names = [
            local_catalog_name + "_group_name_0.1.0",
            local_catalog_name + "_group_app1_0.1.0",
            local_catalog_name + "_group_app2_0.1.0",
            local_catalog_name + "_group_solution1_app1_0.1.0",
            local_catalog_name + "_group_solution2_app1_0.1.0",
            local_catalog_name + "_group_solution3_noparent_0.1.0",
            local_catalog_name + "_group_solution4_app2_0.1.0",
            local_catalog_name + "_group_solution5_app2_0.1.0",
            local_catalog_name + "_group_solution6_noparent_test_0.1.0",
            local_catalog_name + "_group_solution7_long_routines_0.1.0",
            local_catalog_name + "_group_solution8_arguments_0.1.0",
            local_catalog_name + "_group_solution9_throws_exception_0.1.0",
            local_catalog_name + "_group_solution10_uninstall_0.1.0",
            local_catalog_name + "_group_solution13_faultySolution_0.1.0",
            local_catalog_name + "_group_solution_with_steps_0.1.0",
            local_catalog_name + "_solution_with_steps_grouped_0.1.0"
        ]
        for e in env_names:
            if self.album_instance.environment_manager().get_conda_manager().environment_exists(e):
                self.album_instance.environment_manager().get_conda_manager().remove_environment(e)

        self.album_instance.close()
        album_logging._active_logger = {}

        try:
            Path(self.closed_tmp_file.name).unlink()
            self.tmp_dir.cleanup()
        except PermissionError:
            try:
                force_remove(self.tmp_dir.name)
            except PermissionError:
                # todo: fixme! rather sooner than later!
                if sys.platform == 'win32' or sys.platform == 'cygwin':
                    pass
                else:
                    raise

    def run(self, result=None):
        # add watcher to catch any exceptions thrown in threads
        with GlobalExceptionWatcher():
            super(TestIntegrationCoreCommon, self).run(result)

    @staticmethod
    def configure_silent_test_logging(captured_output, logger_name="integration-test"):
        logger = configure_logging(logger_name, loglevel=LogLevel.INFO)
        ch = logging.StreamHandler(captured_output)
        ch.setLevel('INFO')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        return logger

    @staticmethod
    def get_test_solution_path(solution_file="solution0_dummy.py"):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", solution_file)
        return str(path.resolve())

    def fake_install(self, path, create_environment=True) -> Optional[Solution]:
        # add to local catalog
        a = self.album_instance.state_manager().load(path)

        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        if create_environment:
            env_name = "_".join([local_catalog.name(), a.get_identifier()])
            self.album_instance.environment_manager().get_conda_manager().install(Environment(None, env_name, "unusedCachePath"))

        # add to collection, assign to local catalog
        len_catalog_before = len(self.test_collection.get_solutions_by_catalog(local_catalog.catalog_id()))
        self.collection_manager.solutions().add_to_local_catalog(a, path)
        self.collection_manager.solutions().set_installed(local_catalog, a.coordinates())
        self.assertEqual(len_catalog_before + 1, len(self.test_collection.get_solutions_by_catalog(local_catalog.catalog_id())))

        # copy to correct folder
        copy(
            path,
            self.collection_manager.catalogs().get_local_catalog().path().joinpath(
                DefaultValues.cache_path_solution_prefix.value,
                a.coordinates().group(),
                a.coordinates().name(),
                a.coordinates().version(),
                DefaultValues.solution_default_name.value
            )
        )
        return a
