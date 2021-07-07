import logging
import os
import sys
import tempfile
import unittest.mock
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import hips.core as hips
from hips.core.controller.catalog_manager import CatalogManager
from hips.core.controller.conda_manager import CondaManager
from hips.core.controller.deploy_manager import DeployManager
from hips.core.controller.install_manager import InstallManager
from hips.core.controller.remove_manager import RemoveManager
from hips.core.controller.resolve_manager import ResolveManager
from hips.core.controller.run_manager import RunManager
from hips.core.controller.search_manager import SearchManager
from hips.core.controller.test_manager import TestManager
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.model.configuration import HipsConfiguration
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import copy
from hips_runner.logging import push_active_logger


class TestIntegrationCommon(unittest.TestCase):
    test_config_init = """catalogs:
    - %s
    """ % HipsDefaultValues.catalog_url.value

    test_configuration_file = None

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

        # load singletons with test configuration
        self.create_test_config()

    def tearDown(self) -> None:
        # clean all environments specified in test-resources
        for e in ["app1", "app2", "solution3_noparent", "solution6_noparent_test"]:
            if CondaManager().environment_exists(e):
                CondaManager().remove_environment(e)

        try:
            Path(self.closed_tmp_file.name).unlink()
            self.tmp_dir.cleanup()
        except PermissionError:
            # todo: fixme! rather sooner than later!
            if sys.platform == 'win32' or sys.platform == 'cygwin':
                pass

        self.tear_down_singletons()

    @staticmethod
    def tear_down_singletons():
        # todo: This should actually not be necessary - we want to always load the correct singleton - fixme
        HipsConfiguration.instance = None
        HipsCatalogCollection.instance = None
        SearchManager.instance = None
        ResolveManager.instance = None
        CatalogManager.instance = None
        DeployManager.instance = None
        InstallManager.instance = None
        RemoveManager.instance = None
        RunManager.instance = None
        TestManager.instance = None

    @patch('hips.core.model.catalog.Catalog.refresh_index', return_value=None)
    def create_test_config(self, _):
        self.test_configuration_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w", dir=self.tmp_dir.name
        )
        test_config_init = self.test_config_init + "- %s" % str(Path(self.tmp_dir.name).joinpath(
            HipsDefaultValues.catalog_folder_prefix.value, "test_catalog")
        )
        self.test_configuration_file.writelines(test_config_init)
        self.test_configuration_file.close()

        HipsConfiguration.instance = None  # always force reinitialization of the object!
        config = HipsConfiguration(
            base_cache_path=self.tmp_dir.name,
            configuration_file_path=self.test_configuration_file.name
        )

        HipsCatalogCollection.instance = None  # always force reinitialization of the object!
        self.test_catalog_collection = HipsCatalogCollection(configuration=config)

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
        class TestCatalog:
            id = "aCatalog"

        path = TestIntegrationCommon.get_test_solution_path(hips_dependency['name'] + ".py")
        return {"path": path, "catalog": TestCatalog()}

    @staticmethod
    def get_test_solution_path(solution_file="solution0_dummy.py"):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", solution_file)
        return str(path.resolve())

    def fake_install(self, path):
        # add to local catalog
        h = hips.load(path)
        len_before = len(self.test_catalog_collection.local_catalog)
        self.test_catalog_collection.local_catalog.catalog_index.update(h.get_hips_deploy_dict())

        self.assertEqual(len(self.test_catalog_collection.local_catalog), len_before + 1)

        # copy to correct folder
        copy(
            path,
            self.test_catalog_collection.local_catalog.path.joinpath(
                HipsDefaultValues.cache_path_solution_prefix.value,
                h["group"],
                h["name"],
                h["version"],
                HipsDefaultValues.solution_default_name.value
            )
        )