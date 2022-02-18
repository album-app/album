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
from album.core.api.controller.collection.collection_manager import ICollectionManager
from album.core.controller.album_controller import AlbumController
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove, write_dict_to_json
from album.core.utils.operations.git_operations import create_bare_repository, clone_repository, \
    add_files_commit_and_push
from album.runner import album_logging
from album.runner.album_logging import pop_active_logger, LogLevel, configure_logging, get_active_logger
from album.runner.core.model.solution import Solution
from test.global_exception_watcher import GlobalExceptionWatcher


class TestUnitCoreCommon(unittest.TestCase):
    """Base class for all Unittest in album core"""

    def setUp(self):
        """Could initialize default values for each test class. use `_<name>` to skip property setting."""

        self.solution_default_dict = self.get_solution_dict()
        self.configure_test_logging()
        self._setup_tmp_resources()
        self.album: Optional[AlbumController] = None

    def _setup_tmp_resources(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.closed_tmp_file = tempfile.NamedTemporaryFile(delete=False)
        self.closed_tmp_file.close()

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

    @staticmethod
    def get_catalog_meta_dict(name="catalog_local", version="0.1.0", catalog_type="direct"):
        return {"name": name, "version": version, "type": catalog_type}

    def create_test_catalog_no_git(self):
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        # create meta information in src
        CatalogHandler(self.album).create_new(catalog_src, "test", "direct")

        # create cache version
        catalog_cache_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_cache_path.mkdir(parents=True)
        # create meta information in cache
        CatalogHandler(self.album).create_new(catalog_cache_path, "test", "direct")

        catalog = Catalog(0, 'test', catalog_cache_path, src=catalog_src)
        catalog.load_index()
        return catalog

    def collection_manager(self) -> Optional[ICollectionManager]:
        if self.album:
            return self.album.collection_manager()
        return None

    def tearDown(self) -> None:
        if self.collection_manager() is not None and self.collection_manager().get_collection_index() is not None:
            self.collection_manager().get_collection_index().close()
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

    def configure_test_logging(self):
        logger = get_active_logger()
        logger.handlers.clear()
        self.captured_output = StringIO()
        self.logger = configure_logging("unitTest", loglevel=LogLevel.INFO)
        ch = logging.StreamHandler(self.captured_output)
        ch.setLevel('INFO')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        # ch.addFilter(get_message_filter())
        self.logger.addHandler(ch)

    def get_logs(self):
        logs = self.captured_output.getvalue()
        logs = logs.strip()
        return logs.split("\n")

    def create_album_test_instance(self, init_collection=True, init_catalogs=True) -> AlbumController:
        self.album = AlbumController(base_cache_path=Path(self.tmp_dir.name).joinpath("album"))
        self._setup_collection(init_catalogs, init_collection)
        return self.album

    def _setup_collection(self, init_catalogs, init_collection):
        if init_catalogs:
            catalogs_dict = {
                DefaultValues.local_catalog_name.value:
                    Path(self.tmp_dir.name).joinpath("album", DefaultValues.catalog_folder_prefix.value,
                                                     DefaultValues.local_catalog_name.value)
            }
            # mock retrieve_catalog_meta_information as it involves a http request
            with patch(
                    "album.core.controller.collection.catalog_handler.CatalogHandler._retrieve_catalog_meta_information") as retrieve_c_m_i_mock:
                get_initial_catalogs_mock = MagicMock(
                    return_value=catalogs_dict
                )
                self.album.configuration().get_initial_catalogs = get_initial_catalogs_mock
                retrieve_c_m_i_mock.side_effect = [
                    self.get_catalog_meta_dict(),  # local catalog creation call
                    self.get_catalog_meta_dict(),  # local catalog load_index call
                ]
                # create collection
                self.collection_manager().load_or_create()
        elif init_collection:
            # mock retrieve_catalog_meta_information as it involves a http request
            with patch("album.core.controller.collection.catalog_handler.CatalogHandler.add_initial_catalogs"):
                self.collection_manager().load_or_create()

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


class TestCatalogAndCollectionCommon(TestUnitCoreCommon):
    """Test Helper class for TestCollectionManager"""

    def setUp(self):
        super().setUp()

    def set_up_test_catalogs(self, create_album_instance=True):
        test_catalog1_name = "test_catalog"
        test_catalog2_name = "test_catalog2"

        test_catalog1_src = self.create_empty_catalog(test_catalog1_name)
        test_catalog2_src = self.create_empty_catalog(test_catalog2_name)
        self.catalog_list = [
            {
                'catalog_id': 1,
                'deletable': 0,
                'name': test_catalog1_name,
                'path': str(
                    Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, test_catalog1_name)),
                'src': str(test_catalog1_src),
                'type': "direct",
                'branch_name': "main"
            },
            {
                'catalog_id': 2,
                'deletable': 1,
                'name': "default",
                'path': str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "default")),
                'src': str(DefaultValues.default_catalog_src.value),
                'type': "direct",
                'branch_name': "main"
            },
            {
                'catalog_id': 3,
                'deletable': 1,
                'name': test_catalog2_name,
                'path': str(
                    Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "test_catalog2")),
                'src': str(test_catalog2_src),
                'type': "direct",
                'branch_name': "main"
            }
        ]
        if create_album_instance:
            self.create_album_test_instance(init_catalogs=False, init_collection=True)
        self.catalog_handler = self.album.collection_manager().catalogs()
        self.solution_handler = self.album.collection_manager().solutions()

    def create_empty_catalog(self, name):
        catalog_src_path = Path(self.tmp_dir.name).joinpath("my-catalogs", name)
        create_bare_repository(catalog_src_path)

        catalog_clone_path = Path(self.tmp_dir.name).joinpath("my-catalogs-clone", name)

        with clone_repository(catalog_src_path, catalog_clone_path) as repo:
            head = repo.active_branch

            write_dict_to_json(
                catalog_clone_path.joinpath(DefaultValues.catalog_index_metafile_json.value),
                self.get_catalog_meta_dict(name)
            )

            add_files_commit_and_push(
                head,
                [catalog_clone_path.joinpath(DefaultValues.catalog_index_metafile_json.value)],
                "init",
                push=True
            )

        return catalog_src_path

    def fill_catalog_collection(self):
        # insert catalogs in DB from helper list
        for catalog in self.catalog_list:
            self.album.collection_manager().get_collection_index().insert_catalog(
                catalog["name"],
                catalog["src"],
                catalog["path"],
                catalog["deletable"],
                catalog["branch_name"],
                catalog["type"]
            )
        self.assertEqual(self.catalog_list, self.album.collection_manager().get_collection_index().get_all_catalogs())


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
