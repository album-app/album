import gc
import logging
import os
import tempfile
import unittest
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Optional, Generator
from unittest.mock import patch, MagicMock

import git

from album.ci.utils.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from album.core.controller.album_controller import AlbumController
from album.core.controller.collection.collection_manager import CollectionManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.view_operations import get_message_filter
from album.runner import album_logging
from album.runner.album_logging import pop_active_logger, LogLevel, configure_logging
from album.runner.core.model.solution import Solution
from test.global_exception_watcher import GlobalExceptionWatcher


class TestUnitCoreCommon(unittest.TestCase):
    """Base class for all Unittest in album core"""

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.solution_default_dict = self.get_solution_dict()
        self.captured_output = StringIO()
        self.configure_test_logging(self.captured_output)
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()
        self.collection_manager: Optional[CollectionManager] = None
        self.album: Optional[AlbumController] = None

    @staticmethod
    def get_solution_dict():
        return {
            'group': 'tsg',
            'name': 'tsn',
            'description': 'd1',
            'version': 'tsv',
            'album_api_version': 't1',
            'album_version': 'mhv1',
            'license': 'l1',
            'changelog': 'ch1',
            'acknowledgement': 'a1',
            'authors': ['a1', 'a2'],
            'cite': [{'text': 'c1', 'doi': 'doi1', 'url': 'url1'}],
            'tags': ['t1'],
            'documentation': ['do1'],
            'covers': [{'source': 'co1', 'description': ''}],
            'args': [{'name': 'a1', 'type': 'string', 'description': ''}],
            'title': 't1',
            'timestamp': '',
        }

    def tearDown(self) -> None:
        if self.collection_manager is not None and self.collection_manager.get_collection_index() is not None:
            self.collection_manager.get_collection_index().close()
            self.collection_manager = None
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
            super(TestUnitCoreCommon, self).run(result)

    def configure_test_logging(self, stream_handler):
        self.logger = configure_logging("unitTest", loglevel=LogLevel.INFO)
        ch = logging.StreamHandler(stream_handler)
        ch.setLevel('INFO')
        ch.addFilter(get_message_filter())
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def get_logs(self):
        logs = self.logger.handlers[0].stream.getvalue()
        logs = logs.strip()
        return logs.split("\n")

    def create_album_test_instance(self, init_collection=True, init_catalogs=True) -> AlbumController:
        self.album = AlbumController(base_cache_path=Path(self.tmp_dir.name).joinpath("album"))
        self.collection_manager = self.album.collection_manager()

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
                self.collection_manager.load_or_create()
        elif init_collection:
            # mock retrieve_catalog_meta_information as it involves a http request
            with patch("album.core.controller.collection.catalog_handler.CatalogHandler.add_initial_catalogs"):
                self.collection_manager.load_or_create()

        return self.album

    @patch('album.core.utils.operations.solution_operations.get_deploy_dict')
    def create_test_solution_no_env(self, deploy_dict_mock):
        deploy_dict_mock.return_value = self.solution_default_dict
        self.active_solution = Solution(deploy_dict_mock.return_value)
        self.active_solution.init = lambda: None
        self.active_solution.args = []

    @staticmethod
    def get_catalog_db_from_resources(catalog_name):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", "catalogs", "unit", catalog_name,
                                     DefaultValues.catalog_index_file_name.value)
        return path


class TestZenodoCommon(TestUnitCoreCommon):
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


class TestGitCommon(TestUnitCoreCommon):
    """Base class for all Unittest using a album object"""

    def setUp(self):
        super().setUp()
        self.commit_file = None

    @contextmanager
    def create_tmp_repo(self, commit_solution_file=True, create_test_branch=False) -> Generator[git.Repo, None, None]:
        basepath = Path(self.tmp_dir.name).joinpath("testGitRepo")

        repo = git.Repo.init(path=basepath)

        try:
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

            self.commit_file = tmp_file.name
            yield repo

        finally:
            p = repo.working_tree_dir
            repo.close()
            force_remove(p)



class EmptyTestClass:
    pass
