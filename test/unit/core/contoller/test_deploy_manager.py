import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from album.ci.utils.zenodo_api import ZenodoAPI
from album.core.controller.deploy_manager import DeployManager
from album.core.model.default_values import DefaultValues
from album.core.model.coordinates import Coordinates
from test.unit.test_unit_common import TestGitCommon, EmptyTestClass


class TestDeployManager(TestGitCommon):
    def setUp(self) -> None:
        super().setUp()
        self.zenodoAPI = ZenodoAPI('url', 'access_token')
        self.create_test_config()
        self.create_test_solution_no_env()
        self.create_test_collection_manager()

        # add remote catalog
        self.remote_catalog = self.collection_manager.catalogs().add_by_src(DefaultValues.default_catalog_src.value)

        # add local catalog
        catalog_path = Path(self.tmp_dir.name).joinpath("local_catalog")
        catalog_path.mkdir(parents=True)
        with open(catalog_path.joinpath(DefaultValues.catalog_index_metafile_json.value), 'w') as meta:
            meta.writelines("{\"name\":\"local_catalog\", \"version\": \"0.1.0\"}")
        self.local_catalog = self.collection_manager.catalogs().add_by_src(catalog_path)

        self.deploy_manager = DeployManager()

    def tearDown(self) -> None:
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

        # call
        self.deploy_manager.deploy(deploy_path="None",
                                   catalog_name=os.path.basename(self.tmp_dir.name),
                                   dry_run=False,
                                   push_option=False)

        # assert
        self.assertEqual(self.local_catalog, self.deploy_manager._catalog)  # correct catalog chosen
        get_by_name.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_by_src.assert_not_called()  # catalog given by id not url

        _deploy_to_local_catalog.assert_called_once_with(Path("None"))
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
        self.assertEqual(self.remote_catalog, self.deploy_manager._catalog)  # correct catalog chosen
        get_by_name.assert_called_once_with(os.path.basename(self.tmp_dir.name))  # correct id requested
        get_by_src.assert_not_called()  # catalog given by id not url

        _deploy_to_local_catalog.assert_not_called()
        _deploy_to_remote_catalog.assert_called_once_with(Path("None"), False, False, None, None)

    def test__deploy_to_local_catalog(self):
        # prepare
        self.deploy_manager._catalog = self.local_catalog
        self.deploy_manager._active_solution = self.active_solution

        # mocks
        _deploy_routine_in_local_src = MagicMock(return_value=None)
        self.deploy_manager._deploy_routine_in_local_src = _deploy_routine_in_local_src

        _create_merge_request = MagicMock(return_value=None)
        self.deploy_manager._create_merge_request = _create_merge_request

        # catalog mocks
        add = MagicMock(return_value=None)
        self.local_catalog.add = add

        copy_index_from_cache_to_src = MagicMock(return_value=None)
        self.local_catalog.copy_index_from_cache_to_src = copy_index_from_cache_to_src

        # call
        self.deploy_manager._deploy_to_local_catalog(deploy_path="None")

        # assert
        _deploy_routine_in_local_src.assert_called_once_with("None")
        add.assert_called_once_with(self.active_solution)  # index updated
        copy_index_from_cache_to_src.assert_called_once()

        _create_merge_request.assert_not_called()  # local -> no merge request

    def test__deploy_to_remote_catalog(self):
        # prepare
        self.deploy_manager._catalog = self.remote_catalog
        self.deploy_manager._active_solution = self.active_solution

        # mocks
        _deploy_routine_in_local_src = MagicMock(
            return_value=["solution_zip", "dockerfile", "copiedYmlFilePath", ["cover1", "cover2"]]
        )
        self.deploy_manager._deploy_routine_in_local_src = _deploy_routine_in_local_src

        _create_merge_request = MagicMock(return_value=None)
        self.deploy_manager._create_merge_request = _create_merge_request

        # catalog_mocks
        add = MagicMock(return_value=None)
        self.remote_catalog.add = add

        repo = EmptyTestClass()
        repo.working_tree_dir = "myLocalPathOfTheRemoteCatalog"
        retrieve_catalog = MagicMock(return_value=repo)
        self.remote_catalog.retrieve_catalog = retrieve_catalog

        # call
        self.deploy_manager._deploy_to_remote_catalog("None", False, False)

        # assert
        retrieve_catalog.assert_called_once()
        self.assertEqual("myLocalPathOfTheRemoteCatalog", self.deploy_manager._catalog_local_src)
        _deploy_routine_in_local_src.assert_called_once_with("None")
        _create_merge_request.assert_called_once_with(
            ["copiedYmlFilePath", "solution_zip", "dockerfile"] + ["cover1", "cover2"], False, False, None, None
        )

    def test__deploy_routine_in_local_src(self):
        # mocks
        _copy_and_zip = MagicMock(return_value="solution_zip")
        self.deploy_manager._copy_and_zip = _copy_and_zip

        _copy_cover_to_local_src = MagicMock(return_value=["cover1", "cover2"])
        self.deploy_manager._copy_cover_to_local_src = _copy_cover_to_local_src

        _create_docker_file_in_local_src = MagicMock(return_value="dockerfile")
        self.deploy_manager._create_docker_file_in_local_src = _create_docker_file_in_local_src

        _create_yaml_file_in_local_src = MagicMock(return_value="copiedYmlFilePath")
        self.deploy_manager._create_yaml_file_in_local_src = _create_yaml_file_in_local_src

        # call
        self.deploy_manager._deploy_routine_in_local_src("None")

        # assert
        _copy_and_zip.assert_called_once_with("None")
        _create_docker_file_in_local_src.assert_called_once()  # docker file created
        _create_yaml_file_in_local_src.assert_called_once()  # yml created
        _copy_cover_to_local_src.assert_called_once_with("None")  # cover copied

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
        self.deploy_manager.collection_manager = self.collection_manager
        self.deploy_manager._active_solution = self.active_solution

        self.assertEqual("tsg_tsn_tsv", self.deploy_manager.retrieve_head_name())

    @patch('album.core.controller.deploy_manager.add_files_commit_and_push', return_value=True)
    def test__create_merge_request(self, add_files_commit_and_push_mock):
        self.create_tmp_repo()

        self.deploy_manager._repo = self.repo
        self.deploy_manager._active_solution = self.active_solution

        # call
        self.deploy_manager._create_merge_request([self.closed_tmp_file.name], dry_run=True)

        add_files_commit_and_push_mock.assert_called_once_with(
            self.repo.heads[1], [self.closed_tmp_file.name],
            "Adding new/updated tsg_tsn_tsv",
            email=None, push=False, push_options=[], username=None
        )

    @patch('album.core.model.solution.Solution.get_deploy_dict')
    def test__create_yaml_file_in_local_src(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        self.create_tmp_repo()

        self.deploy_manager._catalog = self.collection_manager.catalogs().get_all()[0]
        self.deploy_manager._repo = self.repo
        self.deploy_manager._catalog_local_src = self.repo.working_tree_dir
        self.deploy_manager._active_solution = self.active_solution

        y_path = self.deploy_manager._create_yaml_file_in_local_src()

        self.assertEqual(Path(self.repo.working_tree_dir).joinpath("catalog", "tsg", "tsn", "tsv", "tsn.yml"), y_path)

        f = open(y_path)
        f_content = f.readlines()
        f.close()

        self.assertEqual(["group: tsg\n", "name: tsn\n", "version: tsv\n"], f_content)

    @patch('album.core.model.solution.Solution.get_deploy_dict')
    def test__get_absolute_zip_path(self, deploy_dict_mock):
        deploy_dict_mock.return_value = {"name": "tsn", "group": "tsg", "version": "tsv"}

        # prepare
        self.create_tmp_repo()
        self.deploy_manager._repo = self.repo
        self.deploy_manager._catalog_local_src = self.repo.working_tree_dir
        self.deploy_manager._active_solution = self.active_solution
        self.deploy_manager._catalog = self.collection_manager.catalogs().get_local_catalog()

        result = Path(self.repo.working_tree_dir).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv",
            "_".join(["tsg", "tsn", "tsv"]) + ".zip"
        )

        self.assertEqual(result, self.deploy_manager._get_absolute_zip_path())

    @patch('album.core.controller.deploy_manager.copy', return_value="absPathCopyOfCover")
    def test__copy_cover_to_local_src(self, copy_mock):
        # set covers
        self.active_solution["covers"] = [{"source": "example_cover1.png"}, {"source": "example_cover2.png"}]

        # prepare fake covers and solution_file
        Path(self.tmp_dir.name).joinpath("example_cover1.png").touch()
        Path(self.tmp_dir.name).joinpath("example_cover2.png").touch()
        Path(self.tmp_dir.name).joinpath(DefaultValues.solution_default_name.value).touch()

        self.create_tmp_repo()
        self.deploy_manager._repo = self.repo
        self.deploy_manager._catalog_local_src = self.repo.working_tree_dir
        self.deploy_manager._active_solution = self.active_solution
        self.deploy_manager._catalog = self.collection_manager.catalogs().get_local_catalog()

        tmp_dir = Path(self.tmp_dir.name)
        target_dir = Path(self.repo.working_tree_dir).joinpath(
            DefaultValues.cache_path_solution_prefix.value,
            "tsg",
            "tsn",
            "tsv"
        )

        # assert
        self.assertEqual(["absPathCopyOfCover", "absPathCopyOfCover"],
                         self.deploy_manager._copy_cover_to_local_src(tmp_dir))

        calls = [call(tmp_dir.joinpath("example_cover1.png"), target_dir.joinpath("example_cover1.png")),
                 call(tmp_dir.joinpath("example_cover2.png"), target_dir.joinpath("example_cover2.png"))]
        copy_mock.assert_has_calls(calls)

    @unittest.skip("Needs to be implemented!")
    def test__create_docker_file_in_local_src(self):
        # todo: implement
        pass

    @patch('album.core.controller.deploy_manager.zip_folder', return_value="absPathZipFile")
    @patch('album.core.controller.deploy_manager.zip_paths', return_value="absPathZipFile")
    def test__copy_and_zip(self, zip_path_mock, zip_folder):
        self.create_tmp_repo()
        self.deploy_manager._repo = self.repo
        self.deploy_manager._catalog_local_src = self.repo.working_tree_dir
        self.deploy_manager._active_solution = self.active_solution
        self.deploy_manager._catalog = self.collection_manager.catalogs().get_local_catalog()

        solution_folder_to_deploy_locally = Path(self.tmp_dir.name)
        solution_file_to_deploy_locally = Path(self.tmp_dir.name).joinpath("nice_file.py")
        solution_file_to_deploy_locally.touch()

        # result
        r = Path(self.repo.working_tree_dir).joinpath(
            self.collection_manager.catalogs().get_local_catalog().get_solution_zip_suffix(
                Coordinates("tsg", "tsn", "tsv"))
        )

        # copy and zip a folder
        self.deploy_manager._copy_and_zip(solution_folder_to_deploy_locally)
        zip_folder.assert_called_once_with(solution_folder_to_deploy_locally, r)
        zip_path_mock.assert_not_called()

        # reset
        zip_path_mock.reset_mock()
        zip_folder.reset_mock()

        # copy and zip a file
        self.deploy_manager._copy_and_zip(solution_file_to_deploy_locally)
        zip_path_mock.assert_called_once()
        zip_folder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
