import logging
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import git

from album.ci.utils.zenodo_api import ZenodoAPI, ZenodoDefaultUrl
from album.core.controller.collection.catalog_handler import CatalogHandler
from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.runner import album_logging
from album.runner.album_logging import pop_active_logger
from album.runner.core.model.solution import Solution
from test.test_common import TestCommon


class TestUnitCoreCommon(TestCommon):
    """Base class for all Unittest in album core"""

    def setUp(self):
        super().setUp()
        self.solution_default_dict = self.get_solution_dict()
        self.setup_album_controller()

    def tearDown(self) -> None:
        self.album_controller.close()
        self.captured_output.close()

        while True:
            logger = pop_active_logger()
            if logger == logging.getLogger():
                break

        if self.album_controller:
            self.album_controller.close()

        album_logging._active_logger = {}
        super().tearDown()

    @staticmethod
    def get_solution_dict():
        return {
            'group': 'tsg',
            'name': 'tsn',
            'description': 'd1',
            'version': 'tsv',
            'album_api_version': '0.5.1',
            'album_version': 'mhv1',
            'license': 'l1',
            'changelog': 'ch1',
            'acknowledgement': 'a1',
            'solution_creators': ['a1', 'a2'],
            'cite': [{'text': 'c1', 'doi': 'doi1', 'url': 'url1'}],
            'tags': ['t1'],
            'documentation': ['do1'],
            'covers': [{'source': 'co1', 'description': ''}],
            'args': [{'name': 'a1', 'type': 'string', 'description': ''}],
            'title': 't1',
            'timestamp': '',
            'custom': {
                'my_key': 'my_value'
            }
        }

    def setup_catalog_no_git(self):
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        # create meta information in src
        CatalogHandler(self.album_controller).create_new_metadata(catalog_src, "test", "direct")

        # create cache version
        catalog_cache_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_cache_path.mkdir(parents=True)
        # create meta information in cache
        CatalogHandler(self.album_controller).create_new_metadata(catalog_cache_path, "test", "direct")

        catalog = Catalog(0, 'test', catalog_cache_path, src=catalog_src)
        catalog.load_index()
        return catalog

    @patch('album.core.utils.operations.solution_operations.get_deploy_dict')
    def setup_solution_no_env(self, deploy_dict_mock):
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

    def setup_test_catalogs(self):
        test_catalog1_name = "test_catalog"
        test_catalog2_name = "test_catalog2"

        test_catalog1_src, _ = self.setup_empty_catalog(test_catalog1_name)
        test_catalog2_src, _ = self.setup_empty_catalog(test_catalog2_name)
        self.catalog_list = [
            {
                'catalog_id': 2,
                'name': test_catalog1_name,
                'path': str(
                    Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, test_catalog1_name)),
                'src': str(test_catalog1_src),
                'type': "direct",
                'branch_name': "main",
                'deletable': 0
            },
            {
                'catalog_id': 3,
                'name': "default",
                'path': str(Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "default")),
                'src': str(DefaultValues.default_catalog_src.value),
                'type': "direct",
                'branch_name': "main",
                'deletable': 1
            },
            {
                'catalog_id': 4,
                'name': test_catalog2_name,
                'path': str(
                    Path(self.tmp_dir.name).joinpath(DefaultValues.catalog_folder_prefix.value, "test_catalog2")),
                'src': str(test_catalog2_src),
                'type': "direct",
                'branch_name': "main",
                'deletable': 1
            }
        ]
        self.catalog_handler = self.album_controller.collection_manager().catalogs()
        self.solution_handler = self.album_controller.collection_manager().solutions()

    def fill_catalog_collection(self):
        cache_catalog = self.album_controller.collection_manager().get_collection_index().get_all_catalogs()
        self.assertEqual(1, len(cache_catalog))
        # insert catalogs in DB from helper list
        for catalog in self.catalog_list:
            self.album_controller.collection_manager().get_collection_index().insert_catalog(
                catalog["name"],
                catalog["src"],
                catalog["path"],
                catalog["deletable"],
                catalog["branch_name"],
                catalog["type"]
            )
        self.catalog_list = \
            [self.album_controller.collection_manager().get_collection_index().get_all_catalogs()[
                 0]] + self.catalog_list
        self.assertListEqual(
            self.catalog_list,
            self.album_controller.collection_manager().get_collection_index().get_all_catalogs()
        )


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
    def setup_tmp_repo(self, commit_solution_file=True, create_test_branch=False) -> Generator[git.Repo, None, None]:
        basepath, basepath_clone = self.setup_empty_catalog("testGitRepo")

        repo = git.Repo(basepath_clone)

        try:
            # necessary for CI
            repo.config_writer().set_value("user", "name", "myusername").release()
            repo.config_writer().set_value("user", "email", "myemail").release()

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
                new_head.checkout()

                # add file to new head
                tmp_file = tempfile.NamedTemporaryFile(
                    dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
                )
                tmp_file.close()
                repo.index.add([tmp_file.name])
                repo.git.commit('-m', "branch added %s " % tmp_file.name, '--no-verify')

                # checkout main again
                repo.heads["main"].checkout()

            self.commit_file = tmp_file.name
            yield repo

        finally:
            p = repo.working_tree_dir
            repo.close()
            force_remove(p)


class EmptyTestClass:
    pass
