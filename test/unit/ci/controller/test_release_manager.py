import unittest
from pathlib import Path
from unittest.mock import MagicMock

import git
from album.core.model.default_values import DefaultValues

from album.core.utils.operations.git_operations import configure_git

from album.ci.controller.release_manager import ReleaseManager
from album.core.utils.operations.file_operations import force_remove, write_dict_to_yml
from test.unit.test_unit_core_common import TestUnitCoreCommon, EmptyTestClass


class TestReleaseManager(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()
        self.setup_album_instance()

    @unittest.skip("Needs to be implemented!")
    def test_configure_repo(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_configure_ssh(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test__get_yml_dict(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_zenodo_publish(self):
        # todo: implement!
        pass

    def test_zenodo_upload(self):
        #prepare
        repo_dir = Path(self.tmp_dir.name).joinpath("repo")
        repo_dir.mkdir(parents=True)
        yml_relative_path = Path('solutions', 'group', 'name', 'solution.yml')
        solution_relative_path = Path('solutions', 'group', 'name', 'solution.py')
        with git.Repo.init(repo_dir) as repo:
            configure_git(repo, DefaultValues.catalog_git_email.value, DefaultValues.catalog_git_user.value)
            repo.git.commit('-m', 'init', '--allow-empty')
            yml_file = repo_dir.joinpath(yml_relative_path)
            solution_file = repo_dir.joinpath(solution_relative_path)
            write_dict_to_yml(yml_file, {
                'group': 'group',
                'name': 'name',
                'version': '0.1.0'
            })
            solution_file.touch()
            repo.git.checkout('-b', 'branch')
            repo.git.add(str(solution_file))
            repo.git.commit('-m', 'committed solution')
            repo.git.add(str(yml_file))
            repo.git.commit('-m', 'committed yml')

        #mock
        catalog_path = Path(self.tmp_dir.name).joinpath('test')
        release_manager = ReleaseManager(self.album, 'test', catalog_path, catalog_src=repo_dir, force_retrieve=False)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value = (None, None))
        zenodo_manager = EmptyTestClass()
        deposit = EmptyTestClass()
        deposit.id = "0"
        deposit.metadata = EmptyTestClass()
        deposit.files = []
        deposit.metadata.prereserve_doi = {}
        deposit.metadata.prereserve_doi["doi"] = "doi"
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value = deposit)
        zenodo_upload = MagicMock()
        zenodo_manager.zenodo_upload = zenodo_upload
        release_manager._get_zenodo_manager = MagicMock(return_value = zenodo_manager)

        #test
        release_manager.zenodo_upload('branch', None, None, None)

        # assert
        self.assertEqual(3, zenodo_upload.call_count)
        self.assertTrue(catalog_path.joinpath(yml_relative_path).exists())
        self.assertEqual(str(catalog_path.joinpath(yml_relative_path)), zenodo_upload.call_args_list[0][0][1])
        self.assertTrue(catalog_path.joinpath(solution_relative_path).exists())
        self.assertTrue(str(zenodo_upload.call_args_list[1][0][1]).endswith('solution.zip'))
        force_remove(repo_dir)

    @unittest.skip("Needs to be implemented!")
    def test_update_index(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_commit_changes(self):
        # todo: implement!
        pass
