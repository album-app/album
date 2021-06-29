import os
import pathlib
from unittest.mock import call
from unittest.mock import patch

from hips.ci.utils import ci_utils
from hips.ci.zenodo_api import ZenodoAPI, ZenodoDeposit, ZenodoMetadata, ZenodoFile, DepositStatus
from test.unit.test_common import TestGitCommon


class TestCiUtils(TestGitCommon):

    def setUp(self) -> None:
        self.zenodoAPI = ZenodoAPI('url', 'access_token')

        current_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
        self.dummysolution = str(current_path.joinpath("..", "..", "resources", "solution0_dummy.py"))

    def tearDown(self) -> None:
        super().tearDown()

    def test__parse_solution_name_from_file(self):

        def __compare_res(i, n, e):
            parsed_name, parsed_full = ci_utils._parse_solution_name_from_file_path(i)
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

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_create_with_prereserve_doi')
    def test__zenodo_get_deposit_no_id(self, depo_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit({}, 'url', 'access_token')

        depo_mock.return_value = deposit_expectation
        get_zenodo_mock.return_value = self.zenodoAPI

        deposit_id = None

        deposit = ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)

        self.assertEqual(deposit_expectation, deposit)

        # mocks
        depo_mock.assert_called_once_with("dummysolution")
        get_zenodo_mock.assert_called_once()

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_get')
    def test_zenodo_get_deposit_valid_id_no_result(self, deposit_get_id_mock, get_zenodo_mock):
        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.return_value = []
        deposit_id = "theID"

        with self.assertRaises(RuntimeError) as context:
            ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)
            self.assertIn("Could not find deposit", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_get')
    def test_zenodo_get_deposit_valid_id_published_no_file(self, deposit_get_id_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit({}, 'yet_another_url', 'access_token')
        deposit_expectation.submitted = True

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.return_value = [deposit_expectation]

        deposit_id = "yetAnotherID"

        with self.assertRaises(AttributeError) as context:
            ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)
            self.assertIn("Deposit has no file ", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        deposit_get_id_mock.assert_called_once_with(deposit_id)

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_get')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoDeposit.new_version', return_value=True)
    def test_zenodo_get_deposit_valid_id_published_with_file(self, new_version_mock, deposit_get_id_mock,
                                                              get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "solution0_dummy.py", "id": 1}).__dict__
            ]},
            'yet_another_url',
            'access_token'
        )
        deposit_expectation.submitted = True

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.return_value = [deposit_expectation]

        deposit_id = "andYetAnotherID"

        ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)

        # mocks
        get_zenodo_mock.assert_called_once()
        new_version_mock.assert_called_once()
        deposit_get_id_mock.assert_called_once_with(deposit_id)

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_get')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoDeposit.new_version', return_value=True)
    def test_zenodo_get_deposit_valid_id_unpublished_with_wrong_file(self, new_version_mock, deposit_get_id_mock,
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
            ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)
            self.assertIn("Deposit has no file with the name ", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        new_version_mock.assert_not_called()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_get')
    def test_zenodo_get_deposit_valid_id_unpublished_with_file_no_doi(self, deposit_get_id_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "solution0_dummy.py", "id": 1}).__dict__
            ]},
            'yet_another_url',
            'access_token'
        )

        get_zenodo_mock.return_value = self.zenodoAPI
        deposit_get_id_mock.side_effect = [[], [deposit_expectation]]

        deposit_id = "AnotherAndYetAnotherID"

        with self.assertRaises(RuntimeError) as context:
            ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)
            self.assertIn("Deposit has no prereserved DOI!", str(context.exception))

        # mocks
        get_zenodo_mock.assert_called_once()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.ci.utils.ci_utils.get_zenodo_api')
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoAPI.deposit_get')
    def test_zenodo_get_deposit_valid_id_unpublished_with_file_and_doi(self, deposit_get_id_mock, get_zenodo_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "solution0_dummy.py", "id": 2}).__dict__
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

        deposit = ci_utils.zenodo_get_deposit("dummysolution", self.dummysolution, deposit_id)

        self.assertEqual(deposit_expectation, deposit)

        # mocks
        get_zenodo_mock.assert_called_once()
        calls = [call(deposit_id), call(deposit_id, status=DepositStatus.DRAFT)]
        deposit_get_id_mock.assert_has_calls(calls)

    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoDeposit.update_file', return_value=True)
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoDeposit.create_file', return_value=True)
    def test_zenodo_upload_file_exists(self, create_file_mock, update_file_mock):
        deposit_expectation = ZenodoDeposit(
            {"files": [
                ZenodoFile({"filename": "solution0_dummy.py", "id": 2}).__dict__
            ],
                "metadata": ZenodoMetadata({"prereserve_doi": {"doi": "the_real_doi"}}).__dict__,
                "doi": "wrong_doi"
            },
            'and_yet_another_url',
            'access_token'
        )

        ci_utils.zenodo_upload(deposit_expectation, self.dummysolution)

        create_file_mock.assert_not_called()
        update_file_mock.assert_called_once_with("solution0_dummy.py", self.dummysolution)

    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoDeposit.update_file', return_value=True)
    @patch('hips.ci.utils.ci_utils.zenodo_api.ZenodoDeposit.create_file', return_value=True)
    def test_zenodo_upload_file_not_exists(self, create_file_mock, update_file_mock):
        deposit_expectation = ZenodoDeposit(
            {
                "metadata": ZenodoMetadata({"prereserve_doi": {"doi": "the_real_doi"}}).__dict__,
                "doi": "wrong_doi"
            },
            'and_yet_another_url',
            'access_token'
        )

        ci_utils.zenodo_upload(deposit_expectation, self.dummysolution)

        create_file_mock.assert_called_once_with(self.dummysolution)
        update_file_mock.assert_not_called()
