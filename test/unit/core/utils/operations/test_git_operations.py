import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import album.core.utils.operations.git_operations as git_op
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import copy
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestGitCommon


class TestGitOperations(TestGitCommon):

    def test_checkout_branch(self):
        with self.create_tmp_repo(create_test_branch=True) as repo:
            head = git_op.checkout_branch(repo, "test_branch")

            self.assertTrue(head == repo.heads["test_branch"])
            # todo: assert checked out

    def test_checkout_branch_no_branch(self):
        with self.create_tmp_repo(commit_solution_file=False) as repo:
            with self.assertRaises(IndexError) as context:
                git_op.checkout_branch(repo, "NoValidBranch")

            self.assertTrue("Branch \"NoValidBranch\" not in repository!" in str(context.exception))

    def test__retrieve_files_from_head(self):
        with self.create_tmp_repo() as repo:
            file_of_commit = git_op.retrieve_files_from_head(repo.heads["master"], "solutions")[0]
            self.assertEqual(self.commit_file, file_of_commit)

    def test_retrieve_files_from_head_branch(self):
        with self.create_tmp_repo(create_test_branch=True) as repo:
            file_of_commit = git_op.retrieve_files_from_head(repo.heads["test_branch"], "solutions")[0]

            self.assertEqual(self.commit_file, file_of_commit)

    def test_retrieve_files_from_head_too_many_files(self):
        with self.create_tmp_repo() as repo:
            tmp_file_1 = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            tmp_file_2 = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            tmp_file_1.close()
            tmp_file_2.close()

            repo.index.add([tmp_file_1.name, tmp_file_2.name])
            repo.git.commit('-m', 'message', '--no-verify')

            with self.assertRaises(RuntimeError) as context:
                git_op.retrieve_files_from_head(repo.heads["master"], "solutions")

            self.assertTrue("times, but expected" in str(context.exception))

    def test_retrieve_files_from_head_no_files(self):
        with self.create_tmp_repo(commit_solution_file=False) as repo:
            with self.assertRaises(RuntimeError) as context:
                git_op.retrieve_files_from_head(repo.heads["master"], "solutions")

            self.assertTrue("does not hold pattern" in str(context.exception))

    @patch('album.core.utils.operations.solution_operations.get_deploy_dict', return_value={})
    def test_add_files_commit_and_push(self, _):
        attrs_dict = {"name": "test_solution_name", "group": "test_solution_group", "version": "test_solution_version"}
        active_solution = Solution(attrs_dict)

        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()

        with self.create_tmp_repo() as repo:
            new_head = repo.create_head("test_solution_name")
            new_head.ref = repo.heads["master"]
            new_head.checkout()

            tmp_file_in_repo = Path(repo.working_tree_dir).joinpath(
                "solutions",
                active_solution.coordinates().group(),
                active_solution.coordinates().name(),
                active_solution.coordinates().version(),
                "%s%s" % (active_solution.coordinates().name(), ".py")
            )
            copy(tmp_file.name, tmp_file_in_repo)

            commit_msg = "Adding new/updated %s" % active_solution.coordinates().name()

            git_op.add_files_commit_and_push(new_head, [tmp_file_in_repo], commit_msg, push=False)

            # new branch created
            self.assertTrue("test_solution_name" in repo.branches)

            # commit message included
            for f in repo.iter_commits():
                self.assertEqual("Adding new/updated test_solution_name\n", f.message)
                break

            # correct branch checked out
            self.assertEqual(repo.active_branch.name, "test_solution_name")

    @patch('album.core.utils.operations.solution_operations.get_deploy_dict', return_value={})
    def test_add_files_commit_and_push_no_diff(self, _):
        attrs_dict = {
            "name": "test_solution_name",
            "group": "mygroup",
            "version": "myversion"
        }
        Solution(attrs_dict)

        with self.create_tmp_repo(commit_solution_file=False) as repo:
            new_head = repo.create_head("test_solution_name")
            new_head.checkout()

            with self.assertRaises(RuntimeError):
                git_op.add_files_commit_and_push(new_head, [self.commit_file], "a_wonderful_cmt_msg", push=False)

    def test_configure_git(self):
        with self.create_tmp_repo(commit_solution_file=False) as repo:
            git_op.configure_git(repo, "MyEmail", "MyName")

            self.assertEqual("MyName", repo.config_reader().get_value("user", "name"))
            self.assertEqual("MyEmail", repo.config_reader().get_value("user", "email"))

    def test_download_repository(self):
        p = Path(self.tmp_dir.name).joinpath("testGitDownload")
        # run
        repo = git_op.download_repository(
            DefaultValues._catalog_url.value, p
        )
        repo.close()

        # check
        self.assertIn("album_catalog_index.db", os.listdir(p), "Download failed!")

    def test_retrieve_defaul_mr_push_options(self):
        urls = ["https://docs.gitlab.com/ee/user/project/push_options.html",
                "https://gitlab.com/album-app/album/-/merge_requests",
                "https://github.com/",
                "asdasd"]

        exp = [[], ["merge_request.create"], [], []]

        # run
        res = [git_op.retrieve_default_mr_push_options(url) for url in urls]

        # check
        self.assertListEqual(exp, res)


if __name__ == '__main__':
    unittest.main()
