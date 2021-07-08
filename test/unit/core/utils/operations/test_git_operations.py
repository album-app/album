import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import album.core.utils.operations.git_operations as git_op
from album.core.model.default_values import DefaultValues
from album.core.model.album_base import AlbumClass
from album.core.utils.operations.file_operations import copy, force_remove
from test.unit.test_unit_common import TestGitCommon


class TestGitOperations(TestGitCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_checkout_branch(self):
        self.create_tmp_repo(create_test_branch=True)

        head = git_op.checkout_branch(str(self.repo.working_tree_dir), "test_branch")

        self.assertTrue(head == self.repo.heads["test_branch"])

    def test_checkout_branch_no_branch(self):
        self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(IndexError) as context:
            git_op.checkout_branch(str(self.repo.working_tree_dir), "NoValidBranch")

        self.assertTrue("Branch NoValidBranch not in repository!" in str(context.exception))

    def test__retrieve_single_file(self):
        file = self.create_tmp_repo()

        file_of_commit = git_op.retrieve_single_file_from_head(
            self.repo.heads["master"], "solutions")

        self.assertEqual(file, file_of_commit)

    def test_retrieve_single_file_from_head_branch(self):
        tmp_file = self.create_tmp_repo(create_test_branch=True)

        file_of_commit = git_op.retrieve_single_file_from_head(
            self.repo.heads["test_branch"], "solutions")

        self.assertEqual(tmp_file, file_of_commit)

    def test_retrieve_single_file_from_head_too_many_files(self):
        self.create_tmp_repo()

        tmp_file_1 = tempfile.NamedTemporaryFile(dir=os.path.join(str(self.repo.working_tree_dir), "solutions"),
                                                 delete=False)
        tmp_file_2 = tempfile.NamedTemporaryFile(dir=os.path.join(str(self.repo.working_tree_dir), "solutions"),
                                                 delete=False)
        tmp_file_1.close()
        tmp_file_2.close()

        self.repo.index.add([tmp_file_1.name, tmp_file_2.name])
        self.repo.git.commit('-m', 'message', '--no-verify')

        with self.assertRaises(RuntimeError) as context:
            git_op.retrieve_single_file_from_head(self.repo.heads["master"],
                                                  "solutions")

        self.assertTrue("Pattern found too many times!" in str(context.exception))

    def test_retrieve_single_file_from_head_no_files(self):
        self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(RuntimeError) as context:
            git_op.retrieve_single_file_from_head(self.repo.heads["master"],
                                                  "solutions")

        self.assertTrue("Pattern not found!" in str(context.exception))

    @patch('album.core.model.album_base.AlbumClass.get_deploy_dict', return_value={})
    def test_add_files_commit_and_push(self, _):
        attrs_dict = {"name": "test_solution_name", "group": "test_solution_group", "version": "test_solution_version"}
        active_solution = AlbumClass(attrs_dict)

        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()

        self.create_tmp_repo()
        new_head = self.repo.create_head("test_solution_name")
        new_head.ref = self.repo.heads["master"]
        new_head.checkout()

        tmp_file_in_repo = Path(self.repo.working_tree_dir).joinpath(
            "solutions",
            active_solution['group'],
            active_solution["name"],
            active_solution["version"],
            "%s%s" % (active_solution['name'], ".py")
        )
        copy(tmp_file.name, tmp_file_in_repo)

        commit_mssg = "Adding new/updated %s" % active_solution["name"]

        git_op.add_files_commit_and_push(new_head, [tmp_file_in_repo], commit_mssg,
                                         dry_run=True)

        # new branch created
        self.assertTrue("test_solution_name" in self.repo.branches)

        # commit message included
        for f in self.repo.iter_commits():
            self.assertEqual("Adding new/updated test_solution_name\n", f.message)
            break

        # correct branch checked out
        self.assertEqual(self.repo.active_branch.name, "test_solution_name")

    @patch('album.core.model.album_base.AlbumClass.get_deploy_dict', return_value={})
    def test_add_files_commit_and_push_no_diff(self, _):
        attrs_dict = {
            "name": "test_solution_name",
            "group": "mygroup",
            "version": "myversion"
        }
        AlbumClass(attrs_dict)

        file = self.create_tmp_repo(commit_solution_file=False)

        new_head = self.repo.create_head("test_solution_name")
        new_head.checkout()

        with self.assertRaises(RuntimeError):
            git_op.add_files_commit_and_push(new_head, [file], "a_wonderful_cmt_msg",
                                             dry_run=True)

    def test_configure_git(self):
        self.create_tmp_repo(commit_solution_file=False)

        repo = git_op.configure_git(self.repo, "MyEmail", "MyName")

        self.assertEqual("MyName", repo.config_reader().get_value("user", "name"))
        self.assertEqual("MyEmail", repo.config_reader().get_value("user", "email"))

    @patch('album.core.model.album_base.AlbumClass.get_deploy_dict', return_value={})
    def test_download_repository(self, _):
        # clean
        force_remove(DefaultValues.app_cache_dir.value.joinpath("test"))

        # create album
        self.attrs = {
            "git_repo": "https://github.com/rmccue/test-repository.git",
            "name": "test",
            "group": "mygroup",
            "version": "myversion"
        }
        solution_with_git_repo = AlbumClass(self.attrs)

        # run
        git_op.download_repository(solution_with_git_repo["git_repo"],
                                   DefaultValues.app_cache_dir.value.joinpath(
                                       "test"))

        # check
        self.assertIn("test", os.listdir(str(DefaultValues.app_cache_dir.value)), "Download failed!")

        # ToDo: finish test writing

        # checkout old version of repo

        # run again


        # assert that repo has been updated to head!


if __name__ == '__main__':
    unittest.main()
