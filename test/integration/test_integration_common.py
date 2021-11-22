import logging
import os
import sys
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from typing import Optional

from album.core.model.catalog import Catalog

import album.core as album
from album.api import Album
from album.core import Solution
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.controller.conda_manager import CondaManager
from album.core.model.default_values import DefaultValues
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import copy, force_remove
from album.runner.album_logging import configure_logging, LogLevel
from test.global_exception_watcher import GlobalExceptionWatcher
from test.unit.test_unit_common import TestUnitCommon


class TestIntegrationCommon(unittest.TestCase):

    def setUp(self):
        # tempfile/dirs
        self.tmp_dir = tempfile.TemporaryDirectory()

        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

        # logging
        self.captured_output = StringIO()
        self.configure_silent_test_logging(self.captured_output)

        # load gateway with test configuration
        self.album = Album(base_cache_path=self.tmp_dir.name)
        self.collection_manager = self.album.collection_manager()
        self.collection_manager.load_or_create_collection()
        self.test_collection = self.collection_manager.catalog_collection
        self.assertFalse(self.test_collection.is_empty())

    def get_album(self):
        return self.album

    def add_test_catalog(self) -> Catalog:
        path = Path(self.tmp_dir.name).joinpath("my-catalogs", "test_catalog")
        CatalogHandler.create_new_catalog(path, "test_catalog")
        return self.collection_manager.catalogs().add_by_src(path)

    def tearDown(self) -> None:
        # clean all environments specified in test-resources
        local_catalog_name = str(self.collection_manager.catalogs().get_local_catalog().name)
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
            local_catalog_name + "_group_solution_with_steps_0.1.0",
            local_catalog_name + "_solution_with_steps_grouped_0.1.0"
        ]
        for e in env_names:
            if CondaManager().environment_exists(e):
                CondaManager().remove_environment(e)

        TestUnitCommon.tear_down_singletons()

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
            super(TestIntegrationCommon, self).run(result)

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
    def resolve_solution(solution_dependency, download=False):
        class TestCatalog:
            id = "aCatalog"

        path = TestIntegrationCommon.get_test_solution_path(solution_dependency['name'] + ".py")
        return {"path": path, "catalog": TestCatalog()}

    @staticmethod
    def get_test_solution_path(solution_file="solution0_dummy.py"):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", solution_file)
        return str(path.resolve())

    def fake_install(self, path, create_environment=True) -> Optional[Solution]:
        # add to local catalog
        a = album.load(path)

        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        if create_environment:
            env_name = "_".join([local_catalog.name, a.get_identifier()])
            CondaManager().install(Environment(None, env_name, "unusedCachePath"))

        # add to collection, assign to local catalog
        len_catalog_before = len(self.test_collection.get_solutions_by_catalog(local_catalog.catalog_id))
        self.collection_manager.add_solution_to_local_catalog(a, path)
        self.collection_manager.solutions().set_installed(local_catalog, a.coordinates)
        self.assertEqual(len_catalog_before + 1, len(self.test_collection.get_solutions_by_catalog(local_catalog.catalog_id)))

        # copy to correct folder
        copy(
            path,
            self.collection_manager.catalogs().get_local_catalog().path.joinpath(
                DefaultValues.cache_path_solution_prefix.value,
                a.coordinates.group,
                a.coordinates.name,
                a.coordinates.version,
                DefaultValues.solution_default_name.value
            )
        )
        return a
