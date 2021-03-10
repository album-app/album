import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import call
from unittest.mock import patch

import git
from xdg import xdg_cache_home

import hips
from hips import deploy
from utils.zenodo_api import ZenodoDeposit, DepositStatus, ZenodoFile, ZenodoMetadata, ZenodoAPI


class TestHipsDeploy(unittest.TestCase):

    def tearDown(self) -> None:
        basepath = xdg_cache_home().joinpath("testGitRepo")
        shutil.rmtree(basepath, ignore_errors=True)

    def setUp(self) -> None:
        self.zenodoAPI = ZenodoAPI('url', 'access_token')

        current_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        self.dummysolution = str(current_path.joinpath("..", "..", "resources", "dummysolution.py"))

    def create_tmp_repo(self, commit_solution_file=True, create_test_branch=False):
        basepath = xdg_cache_home().joinpath("testGitRepo")
        shutil.rmtree(basepath, ignore_errors=True)

        repo = git.Repo.init(path=basepath)

        # necessary for CI
        repo.config_writer().set_value("user", "name", "myusername").release()
        repo.config_writer().set_value("user", "email", "myemail").release()

        # initial commit
        init_file = tempfile.NamedTemporaryFile(
            dir=os.path.join(str(repo.working_tree_dir)),
            delete=False
        )
        repo.index.add([os.path.basename(init_file.name)])
        repo.git.commit('-m', "init", '--no-verify')

        if commit_solution_file:
            os.makedirs(os.path.join(str(repo.working_tree_dir), "solutions"), exist_ok=True)
            tmp_file = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"),
                delete=False
            )
            repo.index.add([os.path.join("solutions", os.path.basename(tmp_file.name))])
        else:
            tmp_file = tempfile.NamedTemporaryFile(dir=str(repo.working_tree_dir))
            repo.index.add([os.path.basename(tmp_file.name)])

        repo.git.commit('-m', "added %s " % tmp_file.name, '--no-verify')

        if create_test_branch:
            new_head = repo.create_head("test_branch")
            new_head.checkout()

            # add file to new head
            tmp_file = tempfile.NamedTemporaryFile(
                dir=os.path.join(str(repo.working_tree_dir), "solutions"), delete=False
            )
            repo.index.add([tmp_file.name])
            repo.git.commit('-m', "branch added %s " % tmp_file.name, '--no-verify')

            # checkout master again
            repo.heads["master"].checkout()

        self.repo = repo

        return tmp_file.name

    def test__extract_catalog_name(self):
        self.attrs = {
            "catalog": "https://gitlab.com/ida-mdc/hips-catalog.ext"
        }

        active_hips = hips.Hips(self.attrs)

        self.assertEqual(deploy._extract_catalog_name(active_hips["catalog"]), "hips-catalog")

    def test__hips_deploy_dict(self):

        # base keys
        attrs_dict_result = {}
        for idx, key in enumerate(deploy.deploy_keys):
            attrs_dict_result[key] = str(idx)

        # additional values
        attrs_dict_additional = {
            "this_should_not_appear": "Test"
        }

        # create hips attrs dict
        attrs_dict = {**attrs_dict_result, **attrs_dict_additional}
        assert len(attrs_dict) == len(attrs_dict_additional) + len(attrs_dict_result)

        active_hips = hips.Hips(attrs_dict)

        self.assertEqual(deploy._hips_deploy_dict(active_hips), attrs_dict_result)

    @patch('hips.deploy.modules.download_repository', return_value=True)
    def test_download_catalog(self, dl_mock):
        self.attrs = {
            "catalog": "https://gitlab.com/ida-mdc/hips-catalog.ext"
        }

        active_hips = hips.Hips(self.attrs)

        deploy.download_catalog(active_hips)

        dl_mock.assert_called_once_with("https://gitlab.com/ida-mdc/hips-catalog.ext", "hips-catalog")

    def test__create_markdown_file(self):

        # create hips
        attrs_dict = {}
        for idx, key in enumerate(deploy.deploy_keys):
            attrs_dict[key] = str(idx)
        attrs_dict["name"] = "test_solution_name"
        active_hips = hips.Hips(attrs_dict)

        # paths
        basepath = xdg_cache_home().joinpath("testGitRepo")
        expected_file = basepath.joinpath("_solutions", "test_solution_name.md")

        # create repo
        self.create_tmp_repo()
        os.makedirs(str(basepath.joinpath("_solutions")), exist_ok=True)

        deploy._create_markdown_file(self.repo, active_hips)
        self.assertTrue(os.path.isfile(str(expected_file)))

    def test__copy_solution_to_repository(self):
        attrs_dict = {"name": "test_solution_name"}
        active_hips = hips.Hips(attrs_dict)

        self.create_tmp_repo()

        tmp_file = tempfile.NamedTemporaryFile()

        deploy._copy_solution_to_repository(tmp_file.name, self.repo, active_hips)

        self.assertTrue(os.path.isfile(
            os.path.join(str(self.repo.working_tree_dir), "solutions", "test_solution_name.py")
        ))

    def test__create_merge_request(self):
        attrs_dict = {"name": "test_solution_name"}
        active_hips = hips.Hips(attrs_dict)

        tmp_file = tempfile.NamedTemporaryFile()
        self.create_tmp_repo()

        tmp_file_in_repo = deploy._copy_solution_to_repository(tmp_file.name, self.repo, active_hips)

        deploy._create_merge_request(self.repo, [tmp_file_in_repo], active_hips, dry_run=True)

        # new branch created
        self.assertTrue("test_solution_name" in self.repo.branches)

        # commit message included
        for f in self.repo.iter_commits():
            self.assertEqual("Adding new/updated test_solution_name\n", f.message)
            break

        # correct branch checked out
        self.assertEqual(self.repo.active_branch.name, "test_solution_name")

    def test__create_merge_request_no_diff(self):
        attrs_dict = {"name": "test_solution_name"}
        active_hips = hips.Hips(attrs_dict)

        file = self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(RuntimeError):
            deploy._create_merge_request(self.repo, [file], active_hips, dry_run=True)

    def test__retrieve_soltion_file(self):
        file = self.create_tmp_repo()

        file_of_commit = deploy._retrieve_solution_file(self.repo.heads["master"])

        self.assertEqual(file, file_of_commit)

    def test__retrieve_soltion_file_branch(self):
        tmp_file = self.create_tmp_repo(create_test_branch=True)

        file_of_commit = deploy._retrieve_solution_file(self.repo.heads["test_branch"])

        self.assertEqual(tmp_file, file_of_commit)

    def test__retrieve_soltion_file_too_many_files(self):
        self.create_tmp_repo()

        tmp_file_1 = tempfile.NamedTemporaryFile(dir=os.path.join(str(self.repo.working_tree_dir), "solutions"))
        tmp_file_2 = tempfile.NamedTemporaryFile(dir=os.path.join(str(self.repo.working_tree_dir), "solutions"))

        self.repo.index.add([tmp_file_1.name, tmp_file_2.name])
        self.repo.git.commit('-m', 'message', '--no-verify')

        with self.assertRaises(RuntimeError) as context:
            deploy._retrieve_solution_file(self.repo.heads["master"])

        self.assertTrue("too many solutions" in str(context.exception))

    def test__retrieve_soltion_file_no_files(self):
        self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(RuntimeError) as context:
            deploy._retrieve_solution_file(self.repo.heads["master"])

        self.assertTrue("Found no solution" in str(context.exception))

    def test__checkout_branch(self):
        self.create_tmp_repo(create_test_branch=True)

        head = deploy._checkout_branch(str(self.repo.working_tree_dir), "test_branch")

        self.assertTrue(head == self.repo.heads["test_branch"])

    def test__checkout_branch_no_branch(self):
        self.create_tmp_repo(commit_solution_file=False)

        with self.assertRaises(IndexError) as context:
            deploy._checkout_branch(str(self.repo.working_tree_dir), "NoValidBranch")

        self.assertTrue("Branch NoValidBranch not in repository!" in str(context.exception))

    @patch('hips.deploy.file_operations.get_zenodo_metadata', return_value=12345)
    @patch('hips.deploy._zenodo_get_deposit', return_value=ZenodoDeposit({}, 'url', 'token'))
    def test_get_release_deposit(self, get_depo_mock, get_meta_mock):

        file = self.create_tmp_repo(create_test_branch=True)

        deploy.get_release_deposit(file)

        get_meta_mock.assert_called_once()
        get_depo_mock.assert_called_once_with(file, 12345)

    def test__parse_solution_name_from_file(self):

        def __compare_res(i, n, e):
            parsed_name, parsed_full = deploy._parse_solution_name_from_file_path(i)
            self.assertEqual(parsed_name, n)
            p = ""
            p = p + n if n != "" else p
            p = p + "." + e if e != "" else p
            self.assertEqual(parsed_full, p)

        test_names = [
            "/path/to/solution.whatsoever",
            "relativeName.sol",
            "#1invalid_but-gets*parsed/anyway.ext",
            "noExtension",
            ".noName",  # gets treated as name, not as extension
            "two.ext.ext"
        ]
        __compare_res(test_names[0], "solution", "whatsoever")
        __compare_res(test_names[1], "relativeName", "sol")
        __compare_res(test_names[2], "anyway", "ext")
        __compare_res(test_names[3], "noExtension", "")
        __compare_res(test_names[4], ".noName", "")
        __compare_res(test_names[5], "two.ext", "ext")

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_create_with_prereserve_doi')
    def test__zenodo_get_deposit_no_id(self, depo_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit({}, 'url', 'access_token')

        depo_mock.return_value = deposit_expectation
        get_zenodo_mock.return_value = self.zenodoAPI

        deposit_id = None

        deposit = deploy._zenodo_get_deposit(self.dummysolution, deposit_id)

        self.assertEqual(deposit_expectation, deposit)

        # mocks
        depo_mock.assert_called_once_with("dummysolution")
        get_zenodo_mock.assert_called_once()

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_get')
    def test__zenodo_get_deposit_valid_id_no_result(self, deposit_get_id_mock, get_zenodo_mock):
        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.return_value = []
        deposit_id = "theID"

        with self.assertRaises(RuntimeError) as context:
            deploy._zenodo_get_deposit(self.dummysolution, deposit_id)
            self.assertIn("Could not find deposit", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_get')
    def test__zenodo_get_deposit_valid_id_published_no_file(self, deposit_get_id_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit({}, 'yet_another_url', 'access_token')

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.return_value = [deposit_expectation]

        deposit_id = "yetAnotherID"

        with self.assertRaises(AttributeError) as context:
            deploy._zenodo_get_deposit(self.dummysolution, deposit_id)
            self.assertIn("Deposit has no file ", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        deposit_get_id_mock.assert_called_once_with(deposit_id)

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_get')
    @patch('hips.deploy.zenodo_api.ZenodoDeposit.new_version', return_value=True)
    def test__zenodo_get_deposit_valid_id_published_with_file(self, new_version_mock, deposit_get_id_mock,
                                                              get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "dummysolution.py", "id": 1}).__dict__
            ]},
            'yet_another_url',
            'access_token'
        )

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.return_value = [deposit_expectation]

        deposit_id = "andYetAnotherID"

        deploy._zenodo_get_deposit(self.dummysolution, deposit_id)

        # mocks
        get_zenodo_mock.assert_called_once()
        new_version_mock.assert_called_once()
        deposit_get_id_mock.assert_called_once_with(deposit_id)

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_get')
    @patch('hips.deploy.zenodo_api.ZenodoDeposit.new_version', return_value=True)
    def test__zenodo_get_deposit_valid_id_unpublished_with_wrong_file(self, new_version_mock, deposit_get_id_mock,
                                                                      get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "wrong_solution.py", "id": 1}).__dict__
            ]},
            'yet_another_url',
            'access_token'
        )

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.side_effect = [[], [deposit_expectation]]

        deposit_id = "ThisIsYetAnotherID"

        with self.assertRaises(AttributeError) as context:
            deploy._zenodo_get_deposit(self.dummysolution, deposit_id)
            self.assertIn("Deposit has no file with the name ", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        new_version_mock.assert_not_called()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_get')
    def test__zenodo_get_deposit_valid_id_unpublished_with_file_no_doi(self, deposit_get_id_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "dummysolution.py", "id": 1}).__dict__
            ]},
            'yet_another_url',
            'access_token'
        )

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.side_effect = [[], [deposit_expectation]]

        deposit_id = "AnotherAndYetAnotherID"

        with self.assertRaises(RuntimeError) as context:
            deploy._zenodo_get_deposit(self.dummysolution, deposit_id)
            self.assertIn("Deposit has no prereserved DOI!", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.deploy.__get_zenodo_api')
    @patch('hips.deploy.zenodo_api.ZenodoAPI.deposit_get')
    def test__zenodo_get_deposit_valid_id_unpublished_with_file_and_doi(self, deposit_get_id_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                     ZenodoFile({"filename": "dummysolution.py", "id": 2}).__dict__
                 ],
             "metadata": ZenodoMetadata({"prereserve_doi": {"doi": "the_real_doi"}}).__dict__,
             "doi": "wrong_doi"
             },
            'and_yet_another_url',
            'access_token'
        )

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.side_effect = [[], [deposit_expectation]]

        deposit_id = "AgainAnotherAndYetAnotherID"

        deposit = deploy._zenodo_get_deposit(self.dummysolution, deposit_id)

        self.assertEqual(deposit_expectation, deposit)

        # mocks
        get_zenodo_mock.assert_called_once()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.deploy.zenodo_api.ZenodoDeposit.update_file', return_value=True)
    @patch('hips.deploy.zenodo_api.ZenodoDeposit.create_file', return_value=True)
    def test__zenodo_upload_file_exists(self, create_file_mock, update_file_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                     ZenodoFile({"filename": "dummysolution.py", "id": 2}).__dict__
                 ],
             "metadata": ZenodoMetadata({"prereserve_doi": {"doi": "the_real_doi"}}).__dict__,
             "doi": "wrong_doi"
             },
            'and_yet_another_url',
            'access_token'
        )

        deploy._zenodo_upload(deposit_expectation, self.dummysolution)

        create_file_mock.assert_not_called()
        update_file_mock.assert_called_once_with("dummysolution.py", self.dummysolution)

    @patch('hips.deploy.zenodo_api.ZenodoDeposit.update_file', return_value=True)
    @patch('hips.deploy.zenodo_api.ZenodoDeposit.create_file', return_value=True)
    def test__zenodo_upload_file_not_exists(self, create_file_mock, update_file_mock):
        deposit_expectation = ZenodoDeposit(
            {
                "metadata": ZenodoMetadata({"prereserve_doi": {"doi": "the_real_doi"}}).__dict__,
                "doi": "wrong_doi"
            },
            'and_yet_another_url',
            'access_token'
        )

        deploy._zenodo_upload(deposit_expectation, self.dummysolution)

        create_file_mock.assert_called_once_with(self.dummysolution)
        update_file_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
