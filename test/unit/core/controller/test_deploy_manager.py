import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from album.core.controller.migration_manager import MigrationManager

from album.ci.utils.zenodo_api import ZenodoAPI
from album.core.controller.deploy_manager import DeployManager
from album.runner.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from test.unit.test_unit_common import TestGitCommon, EmptyTestClass


class TestDeployManager(TestGitCommon):
    def setUp(self) -> None:
        super().setUp()
        self.create_album_test_instance()
        self.zenodoAPI = ZenodoAPI('url', 'access_token')
        self.create_test_solution_no_env()

        self.remote_catalog = self.collection_manager.catalogs().add_by_src(DefaultValues.default_catalog_src.value)

        # add a third local catalog
        catalog_path = Path(self.tmp_dir.name).joinpath("local_catalog")
        catalog_path.mkdir(parents=True)
        with open(catalog_path.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as meta:
            meta.writelines("{\"name\":\"local_catalog\", \"version\": \"0.1.0\"}")
        self.local_catalog = self.collection_manager.catalogs().add_by_src(catalog_path)

        self.deploy_manager = DeployManager()

    def tearDown(self) -> None:
        self.remote_catalog.dispose()
        self.local_catalog.dispose()
        super().tearDown()

    @patch('album.core.controller.deploy_manager.load')
    def test_deploy_catalog_name_given_and_local(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        _deploy_to_local_catalog = MagicMock(return_value=None)
        self.deploy_manager._deploy_to_local_catalog = _deploy_to_local_catalog

        _deploy_to_remote_catalog = MagicMock(return_value=None)
        self.deploy_manager._deploy_to_remote_catalog = _deploy_to_remote_catalog

        get_by_name = MagicMock(return_value=self.local_catalog)
        self.collection_manager.catalogs().get_by_name = get_by_name

        get_by_src = MagicMock(return_value=None)
        self.collection_manager.catalogs().get_by_src = get_by_src

        with patch('album.core.controller.migration_manager.MigrationManager.load_index'):
            # call
            self.deploy_manager.deploy(deploy_path="None",
                                       catalog_name=os.path.basename(self.tmp_dir.name),
                                       dry_run=False,
                                       push_option=None)

        # assert
        get_by_name.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_by_src.assert_not_called()  # catalog given by id not url

        _deploy_to_local_catalog.assert_called_once_with(self.local_catalog, self.active_solution, Path("None"), False, False)
        _deploy_to_remote_catalog.assert_not_called()

    @patch('album.core.controller.deploy_manager.load')
    def test_deploy_catalog_name_given_and_remote(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        _deploy_to_local_catalog = MagicMock(return_value=None)
        self.deploy_manager._deploy_to_local_catalog = _deploy_to_local_catalog

        _deploy_to_remote_catalog = MagicMock(return_value=None)
        self.deploy_manager._deploy_to_remote_catalog = _deploy_to_remote_catalog

        get_by_name = MagicMock(return_value=self.remote_catalog)
        self.collection_manager.catalogs().get_by_name = get_by_name

        get_by_src = MagicMock(return_value=None)
        self.collection_manager.catalogs().get_by_src = get_by_src

        # call
        self.deploy_manager.deploy(deploy_path="None",
                                   catalog_name=os.path.basename(self.tmp_dir.name),
                                   dry_run=False,
                                   push_option=False)

        # assert
        get_by_name.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_by_src.assert_not_called()  # catalog given by id not url

        _deploy_to_local_catalog.assert_not_called()
        _deploy_to_remote_catalog.assert_called_once_with(self.remote_catalog, self.active_solution, Path("None"), False, False, None, None)

    @patch('album.core.controller.deploy_manager.DeployManager._deploy_routine_in_local_src', return_value=None)
    @patch('album.core.controller.deploy_manager.DeployManager._create_merge_request', return_value=None)
    def test__deploy_to_local_catalog(self, _create_merge_request, _deploy_routine_in_local_src):

        # catalog mocks
        add = MagicMock(return_value=None)
        self.local_catalog.add = add

        copy_index_from_cache_to_src = MagicMock(return_value=None)
        self.local_catalog.copy_index_from_cache_to_src = copy_index_from_cache_to_src

        # migration mocks
        refresh_index = MagicMock(return_value=None)
        MigrationManager().refresh_index = refresh_index

        # call
        self.deploy_manager._deploy_to_local_catalog(self.local_catalog, self.active_solution, deploy_path="None", dry_run=False, force_deploy=False)

        # assert
        _deploy_routine_in_local_src.assert_called_once_with(self.local_catalog, self.local_catalog.src, self.active_solution, "None")
        add.assert_called_once_with(self.active_solution, force_overwrite=False)  # index updated
        copy_index_from_cache_to_src.assert_called_once()
        refresh_index.assert_called_once_with(self.local_catalog)

        _create_merge_request.assert_not_called()  # local -> no merge request

    @patch('album.core.controller.deploy_manager.DeployManager._deploy_routine_in_local_src', return_value=None)
    @patch('album.core.controller.deploy_manager.DeployManager._create_merge_request', return_value=None)
    def test__deploy_to_local_catalog_dry_run(self, _create_merge_request, _deploy_routine_in_local_src):

        # catalog mocks
        add = MagicMock(return_value=None)
        self.local_catalog.add = add

        copy_index_from_cache_to_src = MagicMock(return_value=None)
        self.local_catalog.copy_index_from_cache_to_src = copy_index_from_cache_to_src

        # migration mocks
        refresh_index = MagicMock(return_value=None)
        MigrationManager().refresh_index = refresh_index

        # call
        self.deploy_manager._deploy_to_local_catalog(self.local_catalog, self.active_solution, deploy_path="None", dry_run=True, force_deploy=False)

        # assert
        _deploy_routine_in_local_src.assert_called_once_with(self.local_catalog, self.local_catalog.src, self.active_solution, "None")
        add.assert_not_called()  # index NOT updated
        copy_index_from_cache_to_src.assert_not_called()  # NOT copied to src
        refresh_index.assert_not_called()  # NOT refreshed from src.

        _create_merge_request.assert_not_called()  # local -> no merge request

    @patch('album.core.controller.deploy_manager.DeployManager._deploy_routine_in_local_src', return_value=["solution_zip", "dockerfile", "copiedYmlFilePath", ["cover1", "cover2"]])
    @patch('album.core.controller.deploy_manager.DeployManager._create_merge_request', return_value=None)
    def test__deploy_to_remote_catalog(self, _create_merge_request, _deploy_routine_in_local_src):

        # catalog_mocks
        add = MagicMock(return_value=None)
        self.remote_catalog.add = add

        repo = EmptyTestClass()
        repo.working_tree_dir = "myLocalPathOfTheRemoteCatalog"
        repo.close = lambda: ()
        retrieve_catalog = MagicMock(return_value=repo)
        self.remote_catalog.retrieve_catalog = retrieve_catalog

        # call
        self.deploy_manager._deploy_to_remote_catalog(self.remote_catalog, self.active_solution, "None", False, False)

        # assert
        retrieve_catalog.assert_called_once()
        _deploy_routine_in_local_src.assert_called_once_with(self.remote_catalog, "myLocalPathOfTheRemoteCatalog", self.active_solution, "None")
        _create_merge_request.assert_called_once_with(self.active_solution, repo,
            ["copiedYmlFilePath", "solution_zip", "dockerfile"] + ["cover1", "cover2"], False, False, None, None
        )

    @patch('album.core.controller.deploy_manager.DeployManager._copy_and_zip', return_value="solution_zip")
    @patch('album.core.controller.deploy_manager.DeployManager._copy_cover_to_local_src', return_value=["cover1", "cover2"])
    @patch('album.core.controller.deploy_manager.DeployManager._create_docker_file_in_local_src', return_value="dockerfile")
    @patch('album.core.controller.deploy_manager.DeployManager._create_yaml_file_in_local_src', return_value="copiedYmlFilePath")
    def test__deploy_routine_in_local_src(self, _create_yaml_file_in_local_src, _create_docker_file_in_local_src, _copy_cover_to_local_src, _copy_and_zip):

        # call
        self.deploy_manager._deploy_routine_in_local_src(None, "", None, "None")

        # assert
        _copy_and_zip.assert_called_once_with(None, "", None, "None")
        _create_docker_file_in_local_src.assert_called_once()  # docker file created
        _create_yaml_file_in_local_src.assert_called_once()  # yml created
        _copy_cover_to_local_src.assert_called_once_with(None, "", None, "None")  # cover copied

    @patch('album.core.controller.deploy_manager.load')
    def test_deploy_catalog_not_given(self, load_mock):
        # mocks
        load_mock.return_value = self.active_solution

        get_catalog_by_src = MagicMock(return_value=self.collection_manager.catalogs().get_local_catalog())
        self.collection_manager.catalogs().get_by_src = get_catalog_by_src

        get_catalog_by_id = MagicMock(None)
        self.collection_manager.catalogs().get_by_name = get_catalog_by_id

        # call
        with self.assertRaises(RuntimeError):
            self.deploy_manager.deploy(deploy_path="myPath",
                                       catalog_name=None,
                                       dry_run=False,
                                       push_option=False)

    def test_retrieve_head_name(self):
        self.assertEqual("tsg_tsn_tsv", DeployManager.retrieve_head_name(self.active_solution))

    @patch('album.core.controller.deploy_manager.add_files_commit_and_push', return_value=True)
    def test__create_merge_request(self, add_files_commit_and_push_mock):
        self.create_tmp_repo()

        # call
        DeployManager._create_merge_request(self.active_solution, self.repo, [self.closed_tmp_file.name], dry_run=True)

        add_files_commit_and_push_mock.assert_called_once_with(
            self.repo.heads[1], [self.closed_tmp_file.name],
            "Adding new/updated tsg_tsn_tsv",
            email=None, push=False, push_options=[], username=None
        )

        self.repo.close()

    @patch('album.core.controller.deploy_manager.get_deploy_dict')
    def test__create_yaml_file_in_local_src(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        self.create_tmp_repo()
        catalog_local_src = self.repo.working_tree_dir

        y_path = DeployManager._create_yaml_file_in_local_src(self.active_solution, catalog_local_src)

        self.assertEqual(Path(self.repo.working_tree_dir).joinpath("solutions", "tsg", "tsn", "tsv", "tsn.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)
        self.repo.close()

    @patch('album.core.utils.operations.solution_operations.get_deploy_dict')
    def test__get_absolute_zip_path(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        # prepare
        self.create_tmp_repo()
        catalog_local_src = self.repo.working_tree_dir
        catalog = self.collection_manager.catalogs().get_local_catalog()

        result = Path(self.repo.working_tree_dir).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv",
            "_".join(["tsg", "tsn", "tsv"]) + ".zip"
        )

        self.assertEqual(result, DeployManager._get_absolute_zip_path(catalog, catalog_local_src, self.active_solution))
        self.repo.close()

    @patch('album.core.controller.deploy_manager.copy', return_value="absPathCopyOfCover")
    def test__copy_cover_to_local_src(self, copy_mock):
        # set covers
        self.active_solution.setup.covers = [{"source": "example_cover1.png"}, {"source": "example_cover2.png"}]

        # prepare fake covers and solution_file
        Path(self.tmp_dir.name).joinpath("example_cover1.png").touch()
        Path(self.tmp_dir.name).joinpath("example_cover2.png").touch()
        Path(self.tmp_dir.name).joinpath(DefaultValues.solution_default_name.value).touch()

        self.create_tmp_repo()
        catalog_local_src = self.repo.working_tree_dir
        catalog = self.collection_manager.catalogs().get_local_catalog()

        tmp_dir = Path(self.tmp_dir.name)
        target_dir = Path(self.repo.working_tree_dir).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv"
        )

        # assert
        self.assertEqual(["absPathCopyOfCover", "absPathCopyOfCover"],
                         DeployManager._copy_cover_to_local_src(catalog, catalog_local_src, self.active_solution, tmp_dir))

        calls = [call(tmp_dir.joinpath("example_cover1.png"), target_dir.joinpath("example_cover1.png")),
                 call(tmp_dir.joinpath("example_cover2.png"), target_dir.joinpath("example_cover2.png"))]
        copy_mock.assert_has_calls(calls)
        self.repo.close()

    @unittest.skip("Needs to be implemented!")
    def test__create_docker_file_in_local_src(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_download_path(self):
        # todo: implement
        pass

    @patch('album.core.controller.deploy_manager.zip_folder', return_value="absPathZipFile")
    @patch('album.core.controller.deploy_manager.zip_paths', return_value="absPathZipFile")
    def test__copy_and_zip(self, zip_path_mock, zip_folder):
        self.create_tmp_repo()
        catalog_local_src = self.repo.working_tree_dir
        catalog = self.collection_manager.catalogs().get_local_catalog()

        solution_folder_to_deploy_locally = Path(self.tmp_dir.name)
        solution_file_to_deploy_locally = Path(self.tmp_dir.name).joinpath("nice_file.py")
        solution_file_to_deploy_locally.touch()

        # result
        r = Path(self.repo.working_tree_dir).joinpath(
            self.collection_manager.catalogs().get_local_catalog().get_solution_zip_suffix(
                Coordinates("tsg", "tsn", "tsv"))
        )

        # copy and zip a folder
        DeployManager._copy_and_zip(catalog, catalog_local_src, self.active_solution, solution_folder_to_deploy_locally)
        zip_folder.assert_called_once_with(solution_folder_to_deploy_locally, r)
        zip_path_mock.assert_not_called()

        # reset
        zip_path_mock.reset_mock()
        zip_folder.reset_mock()

        # copy and zip a file
        DeployManager._copy_and_zip(catalog, catalog_local_src, self.active_solution, solution_file_to_deploy_locally)
        zip_path_mock.assert_called_once()
        zip_folder.assert_not_called()
        self.repo.close()


if __name__ == '__main__':
    unittest.main()
