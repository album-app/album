import logging
import os
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import hips.core as hips
from hips.core.controller.conda_manager import CondaManager
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.model.default_values import HipsDefaultValues
from hips_runner.logging import push_active_logger


class TestIntegrationCommon(unittest.TestCase):
    test_config_init = """catalogs:
    - %s
    """ % HipsDefaultValues.catalog_url.value

    test_catalog_collection_config_file = None

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestIntegrationCommon and cls.setUp is not TestIntegrationCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestIntegrationCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def setUp(self):
        # make sure no active hips are somehow configured!
        while hips.get_active_hips() is not None:
            hips.pop_active_hips()

        # tempfile/dirs
        self.tmp_dir = tempfile.TemporaryDirectory()

        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

        # logging
        self.captured_output = StringIO()
        self.configure_silent_test_logging(self.captured_output)

    def tearDown(self) -> None:
        # clean all environments specified in test-resources
        for e in ["app1", "app2", "solution3_noparent", "solution6_noparent_test"]:
            if CondaManager().environment_exists(e):
                CondaManager().remove_environment(e)

        Path(self.closed_tmp_file.name).unlink()
        self.tmp_dir.cleanup()

        if self.test_catalog_collection_config_file:
            Path(self.test_catalog_collection_config_file.name).unlink()

    @patch('hips.core.model.catalog.Catalog.refresh_index', return_value=None)
    def create_test_config(self, _):
        self.test_catalog_collection_config_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        self.test_config_init += "- " + self.tmp_dir.name
        self.test_catalog_collection_config_file.writelines(self.test_config_init)
        self.test_catalog_collection_config_file.close()

        HipsCatalogCollection.instance = None  # lever out singleton concept
        self.test_catalog_collection = HipsCatalogCollection(self.test_catalog_collection_config_file.name)

        self.assertEqual(len(self.test_catalog_collection.local_catalog), 0)

    @staticmethod
    def configure_silent_test_logging(captured_output, logger_name="integration-test", push=True):
        logger = logging.getLogger(logger_name)

        for handler in logger.handlers:
            logger.removeHandler(handler)

        logger.setLevel('INFO')
        ch = logging.StreamHandler(captured_output)
        ch.setLevel('INFO')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        if push:
            push_active_logger(logger)

        return logger

    @staticmethod
    def resolve_hips(hips_dependency, download=False):
        path = TestIntegrationCommon.get_test_solution_path(hips_dependency['name'] + ".py")
        return {"path": path}

    @staticmethod
    def get_test_solution_path(solution_file="solution0_dummy.py"):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", solution_file)
        return str(path.resolve())
