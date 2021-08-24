import logging
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import git

import album_runner
from album.ci.controller.release_manager import ReleaseManager
from album.ci.controller.zenodo_manager import ZenodoManager
from album.ci.utils.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from album.core import AlbumClass
from album.core.controller.clone_manager import CloneManager
from album.core.controller.collection_manager import CollectionManager
from album.core.controller.conda_manager import CondaManager
from album.core.controller.deploy_manager import DeployManager
from album.core.controller.install_manager import InstallManager
from album.core.controller.migration_manager import MigrationManager
from album.core.controller.remove_manager import RemoveManager
from album.core.controller.run_manager import RunManager
from album.core.controller.search_manager import SearchManager
from album.core.controller.task_manager import TaskManager
from album.core.controller.test_manager import TestManager
from album.core.model.configuration import Configuration
from album.core.model.default_values import DefaultValues
from album.core.server import AlbumServer
from album.core.utils.operations.file_operations import force_remove
from album_runner.logging import pop_active_logger, LogLevel, configure_logging
from test.global_exception_watcher import GlobalExceptionWatcher


class TestUnitCommon(unittest.TestCase):
    """Base class for all Unittest using a album object"""

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.solution_default_dict = self.get_solution_dict()
        self.attrs = {}
        self.captured_output = StringIO()
        self.configure_test_logging(self.captured_output)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

    @staticmethod
    def get_solution_dict():
        return {
            'group': "tsg",
            'name': "tsn",
            'description': "d1",
            'version': "tsv",
            'format_version': "f1",
            'tested_album_version': "t1",
            'min_album_version': "mhv1",
            'license': "l1",
            'git_repo': "g1",
            'authors': "a1",
            'cite': "c1",
            'tags': ["t1"],
            'documentation': "do1",
            'covers': "co1",
            'sample_inputs': ["si1"],
            'sample_outputs': ["so1"],
            'args': [{"action": None}],
            'title': "t1",
            'timestamp': "",
        }

    @staticmethod
    def tear_down_singletons():
        # this is here to make sure all mocks are reset each time a test is executed
        album_runner.logging._active_logger = {}
        TestUnitCommon._delete(AlbumServer)
        TestUnitCommon._delete(Configuration)
        TestUnitCommon._delete(CollectionManager)
        TestUnitCommon._delete(CondaManager)
        TestUnitCommon._delete(DeployManager)
        TestUnitCommon._delete(InstallManager)
        TestUnitCommon._delete(RemoveManager)
        TestUnitCommon._delete(RunManager)
        TestUnitCommon._delete(SearchManager)
        TestUnitCommon._delete(TaskManager)
        TestUnitCommon._delete(TestManager)
        TestUnitCommon._delete(ReleaseManager)
        TestUnitCommon._delete(ZenodoManager)
        TestUnitCommon._delete(MigrationManager)
        TestUnitCommon._delete(CloneManager)

    @staticmethod
    def _delete(singleton):
        if singleton.instance is not None:
            del singleton.instance

    def tearDown(self) -> None:
        self.captured_output.close()

        while True:
            logger = pop_active_logger()
            if logger == logging.getLogger():
                break

        Path(self.closed_tmp_file.name).unlink()
        self.tear_down_singletons()
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

    def create_test_config(self):
        self.create_test_config_in_tmp_dir(self.tmp_dir.name)

    def create_test_catalog_manager(self):
        self.collection_manager = CollectionManager()
        self.catalog_collection = self.collection_manager.catalog_collection

    @patch('album.core.model.environment.Environment.__init__', return_value=None)
    @patch('album.core.model.album_base.AlbumClass.get_deploy_dict')
    def create_test_solution_no_env(self, deploy_dict_mock, _):
        deploy_dict_mock.return_value = self.solution_default_dict
        self.active_solution = AlbumClass(deploy_dict_mock.return_value)
        self.active_solution.init = lambda: None
        self.active_solution.args = []

    @staticmethod
    def create_test_config_in_tmp_dir(tmp_dir_name):
        test_catalog_collection_config_file = Path(tmp_dir_name).joinpath(
            DefaultValues.catalog_collection_json_name.value)
        test_config_init = "{\"catalog_collection_version\": \"0.1.0\"}"
        with open(test_catalog_collection_config_file, 'w') as file:
            file.writelines(test_config_init)
        config = Configuration()
        config.setup(
            base_cache_path=tmp_dir_name,
            configuration_file_path=test_catalog_collection_config_file.name
        )

    @staticmethod
    def get_catalog_db_from_resources(catalog_name):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", "catalogs", "unit", catalog_name,
                                     DefaultValues.catalog_index_file_name.value)
        return path


class TestZenodoCommon(TestUnitCommon):
    """Base class for all Unittests including the ZenodoAPI"""

    access_token_environment_name = 'ZENODO_ACCESS_TOKEN'
    base_url = ZenodoDefaultUrl.sandbox_url.value

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


class TestGitCommon(TestUnitCommon):
    """Base class for all Unittest using a album object"""

    repo = None

    def tearDown(self) -> None:
        if self.repo:
            p = self.repo.working_tree_dir
            del self.repo
            force_remove(p)

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


class EmptyTestClass:
    pass
