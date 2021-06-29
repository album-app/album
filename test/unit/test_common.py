import logging
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import git

from hips.ci.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from hips.core import HipsClass
from hips.core.model.catalog_collection import HipsCatalogCollection
from hips.core.model.default_values import HipsDefaultValues
from hips.core.utils.operations.file_operations import remove_warning_on_error
from hips_runner.logging import push_active_logger, pop_active_logger


class TestHipsCommon(unittest.TestCase):
    """Base class for all Unittest using a hips object"""

    test_config_init = """catalogs:
    - %s
    """ % HipsDefaultValues.catalog_url.value
    test_catalog_collection_config_file = None

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestHipsCommon and cls.setUp is not TestHipsCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestHipsCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""
        self.attrs = {}
        self.captured_output = StringIO()
        self.configure_test_logging(self.captured_output)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

    def tearDown(self) -> None:
        self.captured_output.close()

        while True:
            logger = pop_active_logger()
            if logger == logging.getLogger():
                break

        if self.test_catalog_collection_config_file:
            Path(self.test_catalog_collection_config_file.name).unlink()

        Path(self.closed_tmp_file.name).unlink()
        try:
            self.tmp_dir.cleanup()
        except PermissionError:
            try:
                remove_warning_on_error(self.tmp_dir.name)
            except PermissionError:
                raise

    def configure_test_logging(self, stream_handler):
        self.logger = logging.getLogger("unitTest")

        if not self.logger.hasHandlers():
            self.logger.setLevel('INFO')
            ch = logging.StreamHandler(stream_handler)
            ch.setLevel('INFO')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
            push_active_logger(self.logger)

    def get_logs(self):
        logs = self.logger.handlers[0].stream.getvalue()
        logs = logs.strip()
        return logs.split("\n")

    @patch('hips.core.model.catalog.Catalog.refresh_index', return_value=None)
    def create_test_config(self, _):
        self.test_catalog_collection_config_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        self.test_config_init += "- " + self.tmp_dir.name
        self.test_catalog_collection_config_file.writelines(self.test_config_init)
        self.test_catalog_collection_config_file.close()

        HipsCatalogCollection.instance = None  # lever out concept
        self.test_catalog_collection = HipsCatalogCollection(self.test_catalog_collection_config_file.name)

        self.assertEqual(len(self.test_catalog_collection.local_catalog), 0)

    @patch('hips.core.model.environment.Environment.__init__', return_value=None)
    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict')
    def create_test_hips_no_env(self, deploy_dict_mock, _):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}
        self.active_hips = HipsClass(deploy_dict_mock.return_value)
        self.active_hips.init = lambda: None
        self.active_hips.args = []


class TestZenodoCommon(TestHipsCommon):
    """Base class for all Unittests including the ZenodoAPI"""

    access_token_environment_name = 'ZENODO_ACCESS_TOKEN'
    base_url = ZenodoDefaultUrl.sandbox_url.value

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestZenodoCommon and cls.setUp is not TestZenodoCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestZenodoCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def set_environment_attribute(self, attr_name, env_name):
        try:
            setattr(self, attr_name, os.environ[env_name])
        except KeyError:
            raise KeyError("Environment variable %s not set. Please set environment variable to run tests!" % env_name)

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.access_token = None

        self.set_environment_attribute("access_token", self.access_token_environment_name)

        # create a test deposit
        self.zenodoAPI = ZenodoAPI(self.base_url, self.access_token)
        self.test_deposit = self.zenodoAPI.deposit_create()

        super().setUp()

    def tearDown(self):
        assert self.test_deposit.delete()
        if hasattr(self, "test_deposit2"):
            assert self.test_deposit2.delete()
        super().tearDown()


class TestGitCommon(TestHipsCommon):
    """Base class for all Unittest using a hips object"""

    repo = None

    @classmethod
    def setUpClass(cls):
        """On inherited classes, run our `setUp` method"""
        if cls is not TestGitCommon and cls.setUp is not TestGitCommon.setUp:
            orig_set_up = cls.setUp

            def set_up_override(self, *args, **kwargs):
                TestGitCommon.setUp(self)
                return orig_set_up(self, *args, **kwargs)

            cls.setUp = set_up_override

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        if self.repo:
            p = self.repo.working_tree_dir
            del self.repo
            remove_warning_on_error(p)

        super().tearDown()

    def create_tmp_repo(self, commit_solution_file=True, create_test_branch=False):
        basepath = Path(self.tmp_dir.name).joinpath("testGitRepo")

        repo = git.Repo.init(path=basepath)

        # necessary for CI
        repo.config_writer().set_value("user", "name", "myusername").release()
        repo.config_writer().set_value("user", "email", "myemail").release()

        # initial commit
        init_file = tempfile.NamedTemporaryFile(
            dir=os.path.join(str(repo.working_tree_dir)),
            delete=False
        )
        init_file.close()
        repo.index.add([os.path.basename(init_file.name)])
        repo.git.commit('-m', "init", '--no-verify')

        if commit_solution_file:
            os.makedirs(os.path.join(str(repo.working_tree_dir), "solutions"), exist_ok=True)
            tmp_file = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"),
                delete=False
            )
            tmp_file.close()
            repo.index.add([os.path.join("solutions", os.path.basename(tmp_file.name))])
        else:
            tmp_file = tempfile.NamedTemporaryFile(dir=str(repo.working_tree_dir), delete=False)
            tmp_file.close()
            repo.index.add([os.path.basename(tmp_file.name)])

        repo.git.commit('-m', "added %s " % tmp_file.name, '--no-verify')

        if create_test_branch:
            new_head = repo.create_head("test_branch")
            new_head.ref = repo.heads["master"]  # manually point to master
            new_head.checkout()

            # add file to new head
            tmp_file = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            tmp_file.close()
            repo.index.add([tmp_file.name])
            repo.git.commit('-m', "branch added %s " % tmp_file.name, '--no-verify')

            # checkout master again
            repo.heads["master"].checkout()

        self.repo = repo

        return tmp_file.name
