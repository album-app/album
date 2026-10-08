import os
import tempfile
import unittest
from pathlib import Path
from test.test_common import record_requests_to_remotes
from test.unit.test_unit_core_common import TestGitCommon
from unittest.mock import MagicMock, patch

import git

import album.core.utils.operations.git_operations as git_op
from album.core.model.default_values import DefaultValues
from album.environments.utils.file_operations import copy
from album.runner.core.model.solution import Solution


class TestGitOperations(TestGitCommon):
    def test_checkout_branch(self):
        with self.setup_tmp_repo(create_test_branch=True) as repo:
            head = git_op.checkout_branch(repo, "test_branch")

            self.assertTrue(head == repo.heads["test_branch"])

    def test_checkout_branch_no_branch(self):
        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            with self.assertRaises(IndexError) as context:
                git_op.checkout_branch(repo, "NoValidBranch")

            self.assertTrue(
                'Branch "NoValidBranch" not in repository!' in str(context.exception)
            )

    def test__retrieve_files_from_head(self):
        with self.setup_tmp_repo() as repo:
            file_of_commit = git_op.retrieve_files_from_head_last_commit(
                repo.heads["main"], "solutions"
            )[0]
            self.assertEqual(self.commit_file, file_of_commit)

    def test_retrieve_files_from_head_branch(self):
        with self.setup_tmp_repo(create_test_branch=True) as repo:
            file_of_commit = git_op.retrieve_files_from_head_last_commit(
                repo.heads["test_branch"], "solutions"
            )[0]

            self.assertEqual(self.commit_file, file_of_commit)

    def test_retrieve_files_from_head_too_many_files(self):
        with self.setup_tmp_repo() as repo:
            tmp_file_1 = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            tmp_file_2 = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            tmp_file_1.close()
            tmp_file_2.close()

            repo.index.add([tmp_file_1.name, tmp_file_2.name])
            repo.git.commit("-m", "message", "--no-verify")

            with self.assertRaises(RuntimeError) as context:
                git_op.retrieve_files_from_head_last_commit(
                    repo.heads["main"], "solutions"
                )

            self.assertTrue("times, but expected" in str(context.exception))

    def test_retrieve_files_from_head_no_files(self):
        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            with self.assertRaises(RuntimeError) as context:
                git_op.retrieve_files_from_head_last_commit(
                    repo.heads["main"], "solutions"
                )

            self.assertTrue("does not hold pattern" in str(context.exception))

    def test_retrieve_files_from_head_single_commit(self):
        with self.setup_tmp_repo() as repo:
            # an orphan branch starts a new history, its only commit has no parent
            repo.git.checkout("--orphan", "orphan_branch")
            repo.git.commit("-m", "single commit", "--no-verify")
            self.assertEqual(0, len(repo.heads["orphan_branch"].commit.parents))

            with self.assertRaises(RuntimeError) as context:
                git_op.retrieve_files_from_head_last_commit(
                    repo.heads["orphan_branch"], "solutions"
                )

            self.assertTrue(
                "Cannot execute diff since there is only a single commit!"
                in str(context.exception)
            )

    def test__add_files(self):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()

        tmp_file2 = tempfile.NamedTemporaryFile(delete=False)
        tmp_file2.close()

        tmp_file3 = tempfile.NamedTemporaryFile(delete=False)
        tmp_file3.close()

        with self.setup_tmp_repo() as repo:
            # check no untracked files
            self.assertListEqual([], repo.untracked_files)

            copy(tmp_file.name, Path(repo.working_tree_dir).joinpath("myFile1"))
            copy(tmp_file2.name, Path(repo.working_tree_dir).joinpath("myFile2"))
            copy(tmp_file2.name, Path(repo.working_tree_dir).joinpath("myFile3"))

            # all files untracked
            self.assertListEqual(
                ["myFile1", "myFile2", "myFile3"], repo.untracked_files
            )

            git_op._add_files(repo, ["myFile1", "myFile2"])

            # all but one file added
            self.assertListEqual(["myFile3"], repo.untracked_files)

    @patch(
        "album.core.utils.operations.solution_operations.get_deploy_dict",
        return_value={},
    )
    def test_add_files_commit_and_push(self, _):
        attrs_dict = {
            "name": "test_solution_name",
            "group": "test_solution_group",
            "version": "test_solution_version",
        }
        active_solution = Solution(attrs_dict)

        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()

        with self.setup_tmp_repo() as repo:
            new_head = repo.create_head("test_solution_name")
            new_head.ref = repo.heads["main"]
            new_head.checkout()

            tmp_file_in_repo = Path(repo.working_tree_dir).joinpath(
                "solutions",
                active_solution.coordinates().group(),
                active_solution.coordinates().name(),
                active_solution.coordinates().version(),
                "{}{}".format(active_solution.coordinates().name(), ".py"),
            )
            copy(tmp_file.name, tmp_file_in_repo)

            commit_msg = "Adding new/updated %s" % active_solution.coordinates().name()

            git_op.add_files_commit_and_push(
                new_head, [tmp_file_in_repo], commit_msg, push=False
            )

            # new branch created
            self.assertTrue("test_solution_name" in repo.branches)

            # commit message included
            for f in repo.iter_commits():
                self.assertEqual("Adding new/updated test_solution_name\n", f.message)
                break

            # correct branch checked out
            self.assertEqual(repo.active_branch.name, "test_solution_name")

    @patch(
        "album.core.utils.operations.solution_operations.get_deploy_dict",
        return_value={},
    )
    def test_add_files_commit_and_push_no_diff(self, _):
        attrs_dict = {
            "name": "test_solution_name",
            "group": "mygroup",
            "version": "myversion",
        }
        Solution(attrs_dict)

        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            new_head = repo.create_head("test_solution_name")
            new_head.checkout()

            with self.assertRaises(RuntimeError):
                git_op.add_files_commit_and_push(
                    new_head, [self.commit_file], "a_wonderful_cmt_msg", push=False
                )

    @patch(
        "album.core.utils.operations.solution_operations.get_deploy_dict",
        return_value={},
    )
    def test_add_files_commit_and_push_no_diff_allow_empty(self, _):
        """allow_empty=True must create an empty commit instead of raising."""
        attrs_dict = {
            "name": "test_solution_name",
            "group": "mygroup",
            "version": "myversion",
        }
        Solution(attrs_dict)

        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            new_head = repo.create_head("test_solution_name")
            new_head.checkout()

            initial_commit_count = len(list(repo.iter_commits()))

            git_op.add_files_commit_and_push(
                new_head,
                [self.commit_file],
                "empty_commit_msg",
                push=False,
                allow_empty=True,
            )

            # an empty commit must have been created
            commits = list(repo.iter_commits())
            self.assertEqual(initial_commit_count + 1, len(commits))
            self.assertEqual("empty_commit_msg\n", commits[0].message)

    def test_add_files_commit_and_push_tag_and_delete_tag(self):
        with self.setup_tmp_repo() as repo:
            remote = git.Repo(repo.remote().url)
            new_file = Path(repo.working_tree_dir).joinpath("new_file")

            # the commit and its tag go in one push
            new_file.write_text("deployed")
            with record_requests_to_remotes() as requests:
                git_op.add_files_commit_and_push(
                    repo.heads["main"], [new_file], "deploy", push=True, tag="t"
                )
            self.assertEqual(1, len(requests), requests)
            self.assertEqual(repo.head.commit, remote.heads["main"].commit)
            self.assertEqual(repo.head.commit, remote.tags["t"].commit)

            # the commit and the deletion of the tag go in one push
            new_file.write_text("undeployed")
            with record_requests_to_remotes() as requests:
                git_op.add_files_commit_and_push(
                    repo.heads["main"],
                    [new_file],
                    "undeploy",
                    push=True,
                    delete_tag="t",
                )
            self.assertEqual(1, len(requests), requests)
            self.assertEqual(repo.head.commit, remote.heads["main"].commit)
            self.assertEqual([], remote.tags)
            self.assertEqual([], repo.tags)

    def test_get_local_remote_ref_head_asks_remote_only_when_needed(self):
        with self.setup_tmp_repo() as repo:
            repo.git.remote("set-head", "origin", "main")  # as recorded by a clone

            with record_requests_to_remotes() as requests:
                head = git_op.get_local_remote_ref_head(repo)
            self.assertEqual(repo.heads["main"], head)
            self.assertEqual([], requests)

            with record_requests_to_remotes() as requests:
                head = git_op.get_local_remote_ref_head(repo, ask_remote=True)
            self.assertEqual(repo.heads["main"], head)
            self.assertEqual(1, len(requests), requests)

    def test_init_repository_clean_repository(self):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()

        with self.setup_tmp_repo(create_test_branch=True) as repo:
            repo.heads["test_branch"].checkout()

            # create untracked file
            copy(tmp_file.name, Path(repo.working_tree_dir).joinpath("myFile1"))
            self.assertListEqual(["myFile1"], repo.untracked_files)

            # init repository again
            git_op.init_repository(repo.working_tree_dir)

            # check no untracked files left!
            self.assertListEqual([], repo.untracked_files)
            self.assertEqual("main", repo.active_branch.name)

    def test_checkout_main(self):
        with self.setup_tmp_repo(create_test_branch=True) as repo:
            test_head = repo.heads["test_branch"]
            test_head.checkout()

            self.assertEqual(test_head, repo.active_branch)

            # call
            head = git_op.checkout_main(repo)

            # check
            self.assertEqual(head, repo.active_branch)

    def test_configure_git(self):
        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            git_op.configure_git(repo, "MyEmail", "MyName")

            self.assertEqual("MyName", repo.config_reader().get_value("user", "name"))
            self.assertEqual("MyEmail", repo.config_reader().get_value("user", "email"))

    def test_download_repository(self):
        p = Path(self.tmp_dir.name).joinpath("testGitDownload")
        # run
        repo = git_op.download_repository(DefaultValues._catalog_url.value, p)
        repo.close()

        # check
        self.assertIn("album_catalog_index.json", os.listdir(p), "Download failed!")

    def test_retrieve_defaul_mr_push_options(self):
        urls = [
            "https://docs.gitlab.com/ee/user/project/push_options.html",
            "https://gitlab.com/album-app/album/-/merge_requests",
            "https://github.com/",
            "asdasd",
        ]

        exp = [[], ["merge_request.create"], [], []]

        # run
        res = [git_op.retrieve_default_mr_push_options(url) for url in urls]

        # check
        self.assertListEqual(exp, res)

    @unittest.skip("Needs to be implemented!")
    def test_clone_repository_sparse(self):
        # ToDo: implement
        pass

    @patch("git.Repo.clone_from")
    def test_clone_repository_sparse_closes_repo_on_error(self, clone_from_mock):
        repo_mock = MagicMock()
        clone_from_mock.return_value = repo_mock
        target = Path(self.tmp_dir.name).joinpath("testCloneSparse")

        # run
        with self.assertRaises(ValueError) as context:
            with git_op.clone_repository_sparse("bla", "main", target) as repo:
                self.assertIs(repo_mock, repo)
                raise ValueError("error inside the with body")

        # check
        self.assertEqual("error inside the with body", str(context.exception))
        repo_mock.close.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_clone_repository(self):
        # ToDo: implement
        pass

    @patch("git.Repo.clone_from")
    def test_clone_repository_closes_repo_on_error(self, clone_from_mock):
        repo_mock = MagicMock()
        clone_from_mock.return_value = repo_mock
        target = Path(self.tmp_dir.name).joinpath("testClone")

        # run
        with self.assertRaises(ValueError) as context:
            with git_op.clone_repository(Path("bla"), target) as repo:
                self.assertIs(repo_mock, repo)
                raise ValueError("error inside the with body")

        # check
        self.assertEqual("error inside the with body", str(context.exception))
        repo_mock.close.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_create_bare_repository(self):
        # ToDo: implement
        pass

    def test_add_remove_get_tags(self):
        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            git_op.add_tag(repo, "a")
            git_op.add_tag(repo, "b")
            tags = git_op.get_tags(repo)
            self.assertEqual(["b", "a"], tags)
            git_op.remove_tag(repo, "a")
            tags = git_op.get_tags(repo)
            self.assertEqual(["b"], tags)

    def test_revert(self):
        with self.setup_tmp_repo(commit_solution_file=False) as repo:
            testfolder = Path(repo.working_tree_dir).joinpath("test")
            testfolder.mkdir()
            testfile_a = testfolder.joinpath("a.txt")
            testfile_a.touch()
            repo.git.add(str(testfile_a))
            repo.git.commit("-m", "bla")
            git_op.add_tag(repo, "tag1")
            os.remove(testfile_a)
            testfile_b = Path(repo.working_tree_dir).joinpath("b.txt")
            testfile_c = testfolder.joinpath("c.txt")
            testfile_b.touch()
            testfile_c.touch()
            repo.git.rm(str(testfile_a))
            repo.git.add(str(testfile_b), str(testfile_c))
            repo.git.commit("-m", "bla")
            self.assertTrue(testfile_c.exists())
            self.assertFalse(testfile_a.exists())
            git_op.revert(repo, "tag1", [str(testfolder)])
            self.assertTrue(testfile_a.exists())
            self.assertTrue(testfile_b.exists())
            self.assertFalse(testfile_c.exists())


if __name__ == "__main__":
    unittest.main()
