import os
import shutil
import tempfile
import unittest

from xdg import xdg_cache_home

import hips
import hips.api
import hips.hips_base
import hips_utils.operations.git_operations
from test.unit.test_common import TestGitCommon


class TestGitOperations(TestGitCommon):

    def test__checkout_branch(self):
        self.create_tmp_repo(create_test_branch=True)

        head = hips_utils.operations.git_operations._checkout_branch(str(self.repo.working_tree_dir), "test_branch")

        self.assertTrue(head == self.repo.heads["test_branch"])

    def test__checkout_branch_no_branch(self):
        self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(IndexError) as context:
            hips_utils.operations.git_operations._checkout_branch(str(self.repo.working_tree_dir), "NoValidBranch")

        self.assertTrue("Branch NoValidBranch not in repository!" in str(context.exception))

    def test__retrieve_single_file(self):
        file = self.create_tmp_repo()

        file_of_commit = hips_utils.operations.git_operations._retrieve_single_file_from_head(self.repo.heads["master"], "solutions/")

        self.assertEqual(file, file_of_commit)

    def test__retrieve_single_file_from_head_branch(self):
        tmp_file = self.create_tmp_repo(create_test_branch=True)

        file_of_commit = hips_utils.operations.git_operations._retrieve_single_file_from_head(self.repo.heads["test_branch"], "solutions/")

        self.assertEqual(tmp_file, file_of_commit)

    def test__retrieve_single_file_from_head_too_many_files(self):
        self.create_tmp_repo()

        tmp_file_1 = tempfile.NamedTemporaryFile(dir=os.path.join(str(self.repo.working_tree_dir), "solutions"))
        tmp_file_2 = tempfile.NamedTemporaryFile(dir=os.path.join(str(self.repo.working_tree_dir), "solutions"))

        self.repo.index.add([tmp_file_1.name, tmp_file_2.name])
        self.repo.git.commit('-m', 'message', '--no-verify')

        with self.assertRaises(RuntimeError) as context:
            hips_utils.operations.git_operations._retrieve_single_file_from_head(self.repo.heads["master"], "solutions/")

        self.assertTrue("Pattern found too many times!" in str(context.exception))

    def test__retrieve_single_file_from_head_no_files(self):
        self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(RuntimeError) as context:
            hips_utils.operations.git_operations._retrieve_single_file_from_head(self.repo.heads["master"], "solutions/")

        self.assertTrue("Pattern not found!" in str(context.exception))

    def test__add_files_commit_and_push(self):
        attrs_dict = {"name": "test_solution_name"}
        active_hips = hips.hips_base.HipsClass(attrs_dict)

        tmp_file = tempfile.NamedTemporaryFile()
        self.create_tmp_repo()
        new_head = self.repo.create_head("test_solution_name")
        new_head.ref = self.repo.heads["master"]
        new_head.checkout()

        tmp_file_in_repo = hips_utils.operations.git_operations._copy_solution_to_repository(tmp_file.name, self.repo, active_hips)
        commit_mssg = "Adding new/updated %s" % active_hips["name"]

        hips_utils.operations.git_operations._add_files_commit_and_push(new_head, [tmp_file_in_repo], commit_mssg, dry_run=True)

        # new branch created
        self.assertTrue("test_solution_name" in self.repo.branches)

        # commit message included
        for f in self.repo.iter_commits():
            self.assertEqual("Adding new/updated test_solution_name\n", f.message)
            break

        # correct branch checked out
        self.assertEqual(self.repo.active_branch.name, "test_solution_name")

    def test__add_files_commit_and_push_no_diff(self):
        attrs_dict = {"name": "test_solution_name"}
        active_hips = hips.hips_base.HipsClass(attrs_dict)

        file = self.create_tmp_repo(commit_solution_file=False)

        new_head = self.repo.create_head("test_solution_name")
        new_head.checkout()

        with self.assertRaises(RuntimeError):
            hips_utils.operations.git_operations._add_files_commit_and_push(new_head, [file], "a_wonderful_cmt_msg", dry_run=True)

    def test__copy_solution_to_repository(self):
        attrs_dict = {"name": "test_solution_name"}
        active_hips = hips.hips_base.HipsClass(attrs_dict)

        self.create_tmp_repo()

        tmp_file = tempfile.NamedTemporaryFile()

        hips_utils.operations.git_operations._copy_solution_to_repository(tmp_file.name, self.repo, active_hips)

        self.assertTrue(os.path.isfile(
            os.path.join(str(self.repo.working_tree_dir), "solutions", "test_solution_name.py")
        ))

    def test_download_repository(self):
        # clean
        shutil.rmtree(xdg_cache_home().joinpath("test"), ignore_errors=True)

        # create hips
        self.attrs = {
            "git_repo": "https://github.com/rmccue/test-repository.git",
            "name": "test"
        }
        hips_with_git_repo = hips.hips_base.HipsClass(self.attrs)

        # run
        hips_utils.operations.git_operations.download_repository(hips_with_git_repo["git_repo"], xdg_cache_home().joinpath("test"))

        # check
        self.assertIn("test", os.listdir(str(xdg_cache_home())), "Download failed!")

        # ToDo: finish test writing

        # checkout old version of repo

        # run again
        #ips.public_api.download_hips_repository(hips_with_git_repo)

        # assert that repo has been updated to head!


if __name__ == '__main__':
    unittest.main()
