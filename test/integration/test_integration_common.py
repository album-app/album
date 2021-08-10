import logging
import os
import sys
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import album.core as album
from album.core.controller.conda_manager import CondaManager
from album.core.controller.catalog_manager import CatalogManager
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.model.environment import Environment
from album.core.model.solutions_db import SolutionsDb
from album.core.utils.operations.file_operations import copy
from album_runner.logging import configure_logging, LogLevel
from test.global_exception_watcher import GlobalExceptionWatcher
from test.unit.test_unit_common import TestUnitCommon


class TestIntegrationCommon(unittest.TestCase):
    test_config_init = """catalogs:
    - %s
    """ % DefaultValues.catalog_url.value

    test_configuration_file = None

    def setUp(self):

        # tempfile/dirs
        self.tmp_dir = tempfile.TemporaryDirectory()

        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

        # logging
        self.captured_output = StringIO()
        self.configure_silent_test_logging(self.captured_output)

        # load singletons with test configuration
        self.create_test_config()

        self.create_test_db()

    def tearDown(self) -> None:
        # clean all environments specified in test-resources
        env_names = [
            self.test_catalog_collection.local_catalog.id + "_group_name_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_app1_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_app2_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution3_noparent_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution6_noparent_test_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution7_long_routines_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution1_app1_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution2_app1_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution4_app2_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution5_app2_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_group_solution_with_steps_0.1.0",
            self.test_catalog_collection.local_catalog.id + "_solution_with_steps_grouped_0.1.0"
        ]
        for e in env_names:
            if CondaManager().environment_exists(e):
                CondaManager().remove_environment(e)

        TestUnitCommon.tear_down_singletons()

        try:
            Path(self.closed_tmp_file.name).unlink()
            self.tmp_dir.cleanup()
        except PermissionError:
            # todo: fixme! rather sooner than later!
            if sys.platform == 'win32' or sys.platform == 'cygwin':
                pass

    def run(self, result=None):
        # add watcher to catch any exceptions thrown in threads
        with GlobalExceptionWatcher():
            super(TestIntegrationCommon, self).run(result)

    @patch('album.core.model.catalog.Catalog.refresh_index', return_value=None)
    def create_test_config(self, _):
        self.test_configuration_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w", dir=self.tmp_dir.name
        )
        test_config_init = self.test_config_init + "- %s" % str(Path(self.tmp_dir.name).joinpath(
            "my-catalogs", "test_catalog")
        )
        self.test_configuration_file.writelines(test_config_init)
        self.test_configuration_file.close()

        configuration = Configuration()
        configuration.setup(self.tmp_dir.name, self.test_configuration_file.name)

        self.test_catalog_collection = CatalogManager()
        self.test_catalog_collection.setup()

        self.assertEqual(len(self.test_catalog_collection.local_catalog), 0)

    def create_test_db(self):
        self.test_solution_db = SolutionsDb()
        self.assertTrue(self.test_solution_db.is_empty())

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

    def fake_install(self, path, create_environment=True):
        # add to local catalog
        a = album.load(path)
        d = a.get_deploy_dict()

        if create_environment:
            env_name = "_".join([self.test_catalog_collection.local_catalog.id, d["group"], d["name"], d["version"]])
            Environment(None, env_name, "unusedCachePath").install()

        # add to local catalog
        len_catalog_before = len(self.test_catalog_collection.local_catalog)
        self.test_catalog_collection.local_catalog.catalog_index.update(a.get_deploy_dict())
        self.assertEqual(len(self.test_catalog_collection.local_catalog), len_catalog_before + 1)

        # add to installed solutions_db
        len_solution_db_before = len(self.test_solution_db.get_all_solutions())
        self.test_solution_db.add_solution(
            self.test_catalog_collection.local_catalog.id,
            d["group"],
            d["name"],
            d["version"],
            None
        )
        self.assertEqual(len(self.test_solution_db.get_all_solutions()), len_solution_db_before + 1)

        # copy to correct folder
        copy(
            path,
            self.test_catalog_collection.local_catalog.path.joinpath(
                DefaultValues.cache_path_solution_prefix.value,
                a["group"],
                a["name"],
                a["version"],
                DefaultValues.solution_default_name.value
            )
        )
