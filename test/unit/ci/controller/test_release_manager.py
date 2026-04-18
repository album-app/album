import os
from pathlib import Path
from test.unit.test_unit_core_common import EmptyTestClass, TestUnitCoreCommon
from unittest.mock import MagicMock, patch

import git

from album.ci.controller.release_manager import ReleaseManager
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.git_operations import (
    checkout_branch,
    configure_git,
)
from album.environments.utils.file_operations import (
    force_remove,
    get_dict_from_yml,
    write_dict_to_yml,
)


class TestReleaseManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_album_instance()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _create_source_repo(self, yml_dict=None):
        """Create a local git repo with a branch containing a solution.yml.

        Mirrors how ``_create_merge_request`` works in production: a single
        commit on the branch with all deploy-produced files so that
        ``head.commit.parents[0]`` is the fork point from main.

        Returns (repo_dir, branch_name, yml_relative_path, solution_relative_path).
        """
        if yml_dict is None:
            yml_dict = {"group": "group", "name": "name", "version": "0.1.0"}
        repo_dir = Path(self.tmp_dir.name).joinpath("repo")
        repo_dir.mkdir(parents=True)
        yml_relative_path = Path("solutions", "group", "name", "solution.yml")
        solution_relative_path = Path("solutions", "group", "name", "solution.py")
        with git.Repo.init(repo_dir) as repo:
            configure_git(
                repo,
                DefaultValues.catalog_git_email.value,
                DefaultValues.catalog_git_user.value,
            )
            repo.git.commit("-m", "init", "--allow-empty")
            yml_file = repo_dir.joinpath(yml_relative_path)
            solution_file = repo_dir.joinpath(solution_relative_path)
            yml_file.parent.mkdir(parents=True, exist_ok=True)
            write_dict_to_yml(yml_file, yml_dict)
            solution_file.touch()
            repo.git.checkout("-b", "branch")
            repo.git.add(str(solution_file))
            repo.git.add(str(yml_file))
            repo.git.commit("-m", "deploy commit")
        return repo_dir, "branch", yml_relative_path, solution_relative_path

    def _create_release_manager(self, repo_dir):
        """Create a ReleaseManager pointing at *repo_dir*."""
        catalog_path = Path(self.tmp_dir.name).joinpath("test")
        release_manager = ReleaseManager(
            self.album,
            "test",
            catalog_path,
            catalog_src=repo_dir,
            force_retrieve=False,
        )
        return release_manager, catalog_path

    def _create_mock_deposit(
        self,
        deposit_id="0",
        doi="10.5281/zenodo.5678",
        conceptdoi="10.5281/zenodo.1234",
        conceptrecid="1234",
    ):
        """Create a mock deposit with the most common attributes."""
        deposit = EmptyTestClass()
        deposit.id = deposit_id
        deposit.doi = doi
        deposit.conceptdoi = conceptdoi
        deposit.conceptrecid = conceptrecid
        deposit.submitted = False
        deposit.title = "t1"
        deposit.metadata = EmptyTestClass()
        deposit.metadata.prereserve_doi = {"doi": doi}
        deposit.files = []
        deposit.publish = MagicMock()
        return deposit

    def _create_mock_zenodo_manager(self):
        """Create a mock ZenodoManager with all required methods stubbed."""
        zm = EmptyTestClass()
        zm.zenodo_get_deposit = MagicMock()
        zm.zenodo_upload = MagicMock()
        zm.zenodo_delete = MagicMock()
        zm.get_published_deposit = MagicMock(return_value=None)
        zm.get_latest_version_by_concept = MagicMock(return_value=None)
        zm.resolve_concept_record_id = MagicMock(return_value=None)
        zm.zenodo_get_unpublished_deposit_by_id = MagicMock()
        return zm

    # ------------------------------------------------------------------
    # configure_repo
    # ------------------------------------------------------------------

    def test_configure_repo(self):
        """configure_repo must set user.name and user.email on the repo."""
        repo_dir, _, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        release_manager.configure_repo("myUser", "my@email.com")

        repo = git.Repo(catalog_path)
        self.assertEqual("myUser", repo.config_reader().get_value("user", "name"))
        self.assertEqual(
            "my@email.com", repo.config_reader().get_value("user", "email")
        )
        repo.close()
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # configure_ssh
    # ------------------------------------------------------------------

    def test_configure_ssh_switches_to_ssh_url(self):
        """configure_ssh must change remote URL from https to git@ format."""
        repo_dir, _, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        # trigger clone so the repo exists at catalog_path
        with release_manager._open_repo():
            pass

        # In production catalog_src is an HTTP URL; set it so get_ssh_url
        # can parse the netloc correctly (the clone already happened above).
        release_manager.catalog_src = "https://gitlab.com/myGroup/myCatalog"

        release_manager.configure_ssh("myGroup/myCatalog")

        repo = git.Repo(catalog_path)
        self.assertTrue(
            repo.remote().url.startswith("git@"),
            "Expected ssh URL, got: %s" % repo.remote().url,
        )
        self.assertIn("myGroup/myCatalog", repo.remote().url)
        repo.close()
        force_remove(repo_dir)

    def test_configure_ssh_noop_when_already_ssh(self):
        """configure_ssh must not change the URL if it is already ssh."""
        repo_dir, _, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        with release_manager._open_repo():
            pass

        # manually set the remote to an ssh URL
        repo = git.Repo(catalog_path)
        original_ssh_url = "git@gitlab.com:myGroup/myCatalog.git"
        repo.remote().set_url(original_ssh_url)
        repo.close()

        release_manager.catalog_src = "https://gitlab.com/other/path"
        release_manager.configure_ssh("other/path")

        repo = git.Repo(catalog_path)
        self.assertEqual(original_ssh_url, repo.remote().url)
        repo.close()
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # _get_yml_dict
    # ------------------------------------------------------------------

    def test__get_yml_dict(self):
        """_get_yml_dict must return the yml dict and path from the last commit."""
        yml_input = {"group": "group", "name": "name", "version": "0.1.0"}
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo(yml_input)
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        with release_manager._open_repo() as repo:
            head = checkout_branch(repo, branch)
            yml_dict, yml_file_path = release_manager._get_yml_dict(head)

        self.assertIsInstance(yml_dict, dict)
        self.assertEqual("group", yml_dict["group"])
        self.assertEqual("name", yml_dict["name"])
        self.assertEqual("0.1.0", yml_dict["version"])
        self.assertTrue(
            str(yml_file_path).endswith("solution.yml"),
            "Expected path ending in solution.yml, got: %s" % yml_file_path,
        )
        self.assertTrue(Path(yml_file_path).is_file())
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # zenodo_publish
    # ------------------------------------------------------------------

    @patch("album.ci.controller.release_manager.add_tag")
    def test_zenodo_publish(self, mock_add_tag):
        """zenodo_publish must publish the deposit and tag the repo."""
        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.0",
            "deposit_id": "42",
        }
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        deposit = self._create_mock_deposit(
            deposit_id="42",
            doi="10.5281/zenodo.5678",
            conceptdoi="10.5281/zenodo.1234",
        )

        zenodo_manager = EmptyTestClass()
        zenodo_manager.zenodo_get_unpublished_deposit_by_id = MagicMock(
            return_value=deposit
        )
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_publish(branch, None, None)

        # deposit.publish() must have been called
        deposit.publish.assert_called_once()

        # tag must have been added
        mock_add_tag.assert_called_once()

        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.add_tag")
    def test_zenodo_publish_skips_when_already_published(self, mock_add_tag):
        """zenodo_publish must skip publish when deposit is already published."""
        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.0",
            "deposit_id": "42",
            "doi": "10.5281/zenodo.42",
        }
        repo_dir, branch, _, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        from album.ci.utils.zenodo_api import InvalidResponseStatusError

        published_deposit = self._create_mock_deposit(
            deposit_id="42",
            doi="10.5281/zenodo.5678",
            conceptdoi="10.5281/zenodo.1234",
        )

        zenodo_manager = EmptyTestClass()
        # Simulate 404 from unpublished query (deposit is already published)
        zenodo_manager.zenodo_get_unpublished_deposit_by_id = MagicMock(
            side_effect=InvalidResponseStatusError("NotFound")
        )
        zenodo_manager.get_published_deposit = MagicMock(return_value=published_deposit)
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_publish(branch, None, None)

        # publish() must NOT have been called (already published)
        published_deposit.publish.assert_not_called()

        # get_published_deposit must have been consulted with doi
        zenodo_manager.get_published_deposit.assert_called_once_with(
            "42", doi="10.5281/zenodo.42"
        )

        # tag must still have been added
        mock_add_tag.assert_called_once()

        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.add_tag")
    def test_zenodo_publish_skips_via_records_api_fallback(self, mock_add_tag):
        """zenodo_publish must succeed when the deposit is already published
        and only reachable via the records API (deposits API returns 404).

        Unlike test_zenodo_publish_skips_when_already_published, this test
        does NOT mock get_published_deposit; it mocks the underlying
        ZenodoAPI methods so the internal except-Exception fallback inside
        get_published_deposit is exercised. This is the regression test for
        InvalidResponseStatusError formerly inheriting from BaseException.
        """
        from album.ci.controller.zenodo_manager import ZenodoManager
        from album.ci.utils.zenodo_api import InvalidResponseStatusError

        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.1",
            "deposit_id": "19553456",
        }
        repo_dir, branch, _, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        # Build a real ZenodoManager but with a mocked query object
        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()

        # 1) zenodo_get_unpublished_deposit_by_id → 404 (not a draft)
        zm.query.deposit_get_by_id.side_effect = InvalidResponseStatusError(
            "Error 'NotFound' occurred. See Log for detailed information!"
        )

        # 2) records API → returns the published deposit
        published_record = self._create_mock_deposit(
            deposit_id="19553456",
            doi="10.5281/zenodo.19553456",
            conceptdoi="10.5281/zenodo.6410027",
            conceptrecid="6410027",
        )
        published_record.submitted = True
        zm.query.records_get.return_value = [published_record]

        release_manager._get_zenodo_manager = MagicMock(return_value=zm)

        release_manager.zenodo_publish(branch, None, None)

        # deposit_get_by_id was called (and failed)
        self.assertGreaterEqual(zm.query.deposit_get_by_id.call_count, 1)

        # records_get must have been called as fallback
        zm.query.records_get.assert_called_once_with(record_id="19553456")

        # publish() must NOT have been called (already published)
        published_record.publish.assert_not_called()

        # tag must still have been added
        mock_add_tag.assert_called_once()

        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.add_tag")
    def test_zenodo_publish_skips_via_doi_search_fallback(self, mock_add_tag):
        """zenodo_publish must succeed when the deposit is already published
        but BOTH the deposit API and the direct records API return 404.

        This is the exact scenario from https://zenodo.org/records/19553456 :
        after Zenodo's migration to InvenioRDM, the numeric DOI suffix no
        longer matches the record's API PID, so direct lookups fail.  The
        DOI-based search (``/api/records?q=doi:"..."``) still finds it.

        The test exercises the full fallback chain:
        deposit_get_by_id → 404, records_get(record_id=) → 404,
        records_get(q=doi:"...") → found.
        """
        from album.ci.controller.zenodo_manager import ZenodoManager
        from album.ci.utils.zenodo_api import InvalidResponseStatusError

        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.1",
            "deposit_id": "19553456",
            "doi": "10.5281/zenodo.19553456",
        }
        repo_dir, branch, _, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()

        # deposit API → 404
        zm.query.deposit_get_by_id.side_effect = InvalidResponseStatusError("NotFound")

        # records API: direct lookup → 404, DOI search → found
        published_record = self._create_mock_deposit(
            deposit_id="19553456",
            doi="10.5281/zenodo.19553456",
            conceptdoi="10.5281/zenodo.6410027",
            conceptrecid="6410027",
        )
        published_record.submitted = True

        def records_get_side_effect(**kwargs):
            if "record_id" in kwargs and kwargs["record_id"]:
                raise InvalidResponseStatusError("NotFound")
            if "q" in kwargs and "doi:" in kwargs["q"]:
                return [published_record]
            raise InvalidResponseStatusError("NotFound")

        zm.query.records_get.side_effect = records_get_side_effect

        release_manager._get_zenodo_manager = MagicMock(return_value=zm)

        release_manager.zenodo_publish(branch, None, None)

        # records_get called twice: direct lookup (failed) + DOI search (found)
        self.assertEqual(2, zm.query.records_get.call_count)
        zm.query.records_get.assert_any_call(record_id="19553456")
        zm.query.records_get.assert_any_call(q='doi:"10.5281/zenodo.19553456"')

        # publish() must NOT have been called (already published)
        published_record.publish.assert_not_called()

        # tag must still have been added
        mock_add_tag.assert_called_once()

        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.add_tag")
    def test_zenodo_publish_skips_via_records_api_fallback(self, mock_add_tag):
        """zenodo_publish must succeed when the deposit is already published
        and only reachable via the records API (deposits API returns 404).

        This is an end-to-end test for the exact scenario encountered with
        https://zenodo.org/records/19553456 — the deposits API returns 404
        for a published record that the authenticated user does not own via
        the deposit endpoint, but the records API returns it successfully.

        Unlike test_zenodo_publish_skips_when_already_published, this test
        does NOT mock get_published_deposit; it mocks the underlying
        ZenodoAPI methods so the internal except-Exception fallback inside
        get_published_deposit is exercised. This is the regression test for
        InvalidResponseStatusError formerly inheriting from BaseException.
        """
        from album.ci.controller.zenodo_manager import ZenodoManager
        from album.ci.utils.zenodo_api import InvalidResponseStatusError

        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.1",
            "deposit_id": "19553456",
        }
        repo_dir, branch, _, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        # Build a real ZenodoManager but with a mocked query object
        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()

        # 1) zenodo_get_unpublished_deposit_by_id → 404 (not a draft)
        #    We need to make the real method raise, so we wire it through
        #    the underlying _zenodo_get_unpublished which calls deposit_get_by_id.
        zm.query.deposit_get_by_id.side_effect = InvalidResponseStatusError(
            "Error 'NotFound' occurred. See Log for detailed information!"
        )

        # 2) records API → returns the published deposit
        published_record = self._create_mock_deposit(
            deposit_id="19553456",
            doi="10.5281/zenodo.19553456",
            conceptdoi="10.5281/zenodo.6410027",
            conceptrecid="6410027",
        )
        published_record.submitted = True
        zm.query.records_get.return_value = [published_record]

        release_manager._get_zenodo_manager = MagicMock(return_value=zm)

        release_manager.zenodo_publish(branch, None, None)

        # deposit_get_by_id was called (and failed) — at least once for the
        # unpublished query and once inside get_published_deposit
        self.assertGreaterEqual(zm.query.deposit_get_by_id.call_count, 1)

        # records_get must have been called as fallback
        zm.query.records_get.assert_called_once_with(record_id="19553456")

        # publish() must NOT have been called (already published)
        published_record.publish.assert_not_called()

        # tag must still have been added
        mock_add_tag.assert_called_once()

        force_remove(repo_dir)

    def test_zenodo_upload(self):
        # prepare
        repo_dir, branch, yml_relative_path, solution_relative_path = (
            self._create_source_repo()
        )

        # mock
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))
        zenodo_manager = self._create_mock_zenodo_manager()
        deposit = self._create_mock_deposit(
            deposit_id="0", doi="doi", conceptdoi="conceptdoi"
        )
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value=deposit)
        zenodo_upload = MagicMock()
        zenodo_manager.zenodo_upload = zenodo_upload
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        # test
        release_manager.zenodo_upload(branch, None, None, None)

        # assert — solution.yml individually + solution.zip with full directory
        self.assertEqual(2, zenodo_upload.call_count)
        self.assertTrue(catalog_path.joinpath(yml_relative_path).exists())
        self.assertTrue(catalog_path.joinpath(solution_relative_path).exists())
        uploaded_names = {
            Path(call[0][1]).name for call in zenodo_upload.call_args_list
        }
        self.assertEqual({"solution.yml", "solution.zip"}, uploaded_names)
        force_remove(repo_dir)

    def test_zenodo_upload_skips_when_already_published(self):
        """zenodo_upload must skip upload when the latest concept version
        matches the deploy version (pipeline re-run after partial failure)."""
        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.0",
            "deposit_id": "99",
        }
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        published_deposit = self._create_mock_deposit(
            deposit_id="99",
            doi="10.5281/zenodo.99",
            conceptdoi="10.5281/zenodo.50",
        )
        published_deposit.version = "0.1.0"  # matches deploy version

        zenodo_manager = self._create_mock_zenodo_manager()
        zenodo_manager.resolve_concept_record_id = MagicMock(return_value="50")
        zenodo_manager.get_latest_version_by_concept = MagicMock(
            return_value=published_deposit
        )
        zenodo_upload_mock = MagicMock()
        zenodo_manager.zenodo_upload = zenodo_upload_mock
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        report_file = Path(self.tmp_dir.name).joinpath("report.yml")

        release_manager.zenodo_upload(branch, None, None, report_file)

        # upload must NOT have been called
        zenodo_upload_mock.assert_not_called()
        zenodo_manager.zenodo_get_deposit.assert_not_called()

        # concept-level lookup must have been used
        zenodo_manager.resolve_concept_record_id.assert_called_once_with("99", None)
        zenodo_manager.get_latest_version_by_concept.assert_called_once_with("50")

        # solution.yml must be updated with existing DOI
        updated_yml = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertEqual("10.5281/zenodo.99", updated_yml["doi"])
        self.assertEqual("99", updated_yml["deposit_id"])
        self.assertEqual("10.5281/zenodo.50", updated_yml["conceptdoi"])

        # report must be created
        self.assertTrue(report_file.exists())

        force_remove(repo_dir)

    def test_zenodo_upload_skips_when_version_in_metadata(self):
        """The records API returns version=None at top level; the semantic
        version lives in metadata.version. The fallback must work."""
        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.1",
            "deposit_id": "6410028",
        }
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        # Mimic real Zenodo records API: top-level version is None,
        # semantic version only in metadata.version.
        published_deposit = self._create_mock_deposit(
            deposit_id="19553456",
            doi="10.5281/zenodo.19553456",
            conceptdoi="10.5281/zenodo.6410027",
        )
        published_deposit.version = None  # records API returns None here
        published_deposit.metadata.version = "0.1.1"  # this is where it lives

        zenodo_manager = self._create_mock_zenodo_manager()
        zenodo_manager.resolve_concept_record_id = MagicMock(return_value="6410027")
        zenodo_manager.get_latest_version_by_concept = MagicMock(
            return_value=published_deposit
        )
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        report_file = Path(self.tmp_dir.name).joinpath("report.yml")
        release_manager.zenodo_upload(branch, None, None, report_file)

        # upload must have been skipped (same version)
        zenodo_manager.zenodo_get_deposit.assert_not_called()
        zenodo_manager.zenodo_upload.assert_not_called()

        # report with existing DOI
        self.assertTrue(report_file.exists())

        updated_yml = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertEqual("10.5281/zenodo.19553456", updated_yml["doi"])

        force_remove(repo_dir)

    def test_zenodo_upload_rejects_older_version(self):
        """zenodo_upload must raise when deploy version < latest on Zenodo."""
        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.1.0",
            "deposit_id": "99",
        }
        repo_dir, branch, _, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        latest_deposit = self._create_mock_deposit(
            deposit_id="100",
            doi="10.5281/zenodo.100",
            conceptdoi="10.5281/zenodo.50",
        )
        latest_deposit.version = "0.2.0"  # newer than deploy 0.1.0

        zenodo_manager = self._create_mock_zenodo_manager()
        zenodo_manager.resolve_concept_record_id = MagicMock(return_value="50")
        zenodo_manager.get_latest_version_by_concept = MagicMock(
            return_value=latest_deposit
        )
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        with self.assertRaises(RuntimeError) as ctx:
            release_manager.zenodo_upload(branch, None, None, None)

        self.assertIn("older than", str(ctx.exception))
        self.assertIn("0.1.0", str(ctx.exception))
        self.assertIn("0.2.0", str(ctx.exception))

        # upload must NOT have been called
        zenodo_manager.zenodo_get_deposit.assert_not_called()

        force_remove(repo_dir)

    def test_zenodo_upload_overrides_stale_deposit_id(self):
        """When deposit_id from yml points to an old version, it must be
        overridden with the latest deposit so new_version() chains correctly."""
        yml_dict = {
            "group": "group",
            "name": "name",
            "version": "0.2.0",
            "deposit_id": "80",  # stale — points to v0.1.0
        }
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo(yml_dict)
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        latest_deposit = self._create_mock_deposit(
            deposit_id="90",
            doi="10.5281/zenodo.90",
            conceptdoi="10.5281/zenodo.50",
        )
        latest_deposit.version = "0.1.0"  # older than deploy 0.2.0

        new_draft = self._create_mock_deposit(
            deposit_id="91",
            doi="10.5281/zenodo.91",
            conceptdoi="10.5281/zenodo.50",
        )

        zenodo_manager = self._create_mock_zenodo_manager()
        zenodo_manager.resolve_concept_record_id = MagicMock(return_value="50")
        zenodo_manager.get_latest_version_by_concept = MagicMock(
            return_value=latest_deposit
        )
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value=new_draft)
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_upload(branch, None, None, None)

        # zenodo_get_deposit must have been called with the LATEST deposit id
        # (90), not the stale one (80)
        call_args = zenodo_manager.zenodo_get_deposit.call_args
        self.assertEqual("90", call_args[0][1])

        force_remove(repo_dir)

    def test_zenodo_upload_includes_subdirectory_files_via_zip(self):
        """Subdirectory files must be included in solution.zip, plus
        individual preview files (solution.yml, covers) are uploaded."""
        yml_dict = {"group": "group", "name": "name", "version": "0.1.0"}
        repo_dir = Path(self.tmp_dir.name).joinpath("repo")
        repo_dir.mkdir(parents=True)
        yml_relative_path = Path("solutions", "group", "name", "solution.yml")
        solution_relative_path = Path("solutions", "group", "name", "solution.py")
        nested_file_relative = Path(
            "solutions", "group", "name", "src", "main", "java", "Main.java"
        )
        cover_relative = Path("solutions", "group", "name", "cover.png")

        with git.Repo.init(repo_dir) as repo:
            configure_git(
                repo,
                DefaultValues.catalog_git_email.value,
                DefaultValues.catalog_git_user.value,
            )
            repo.git.commit("-m", "init", "--allow-empty")

            repo.git.checkout("-b", "branch")
            yml_file = repo_dir.joinpath(yml_relative_path)
            solution_file = repo_dir.joinpath(solution_relative_path)
            nested_file = repo_dir.joinpath(nested_file_relative)
            cover_file = repo_dir.joinpath(cover_relative)
            yml_file.parent.mkdir(parents=True, exist_ok=True)
            nested_file.parent.mkdir(parents=True, exist_ok=True)
            write_dict_to_yml(yml_file, yml_dict)
            solution_file.touch()
            nested_file.write_text("class Main {}")
            cover_file.write_bytes(b"\x89PNG")
            repo.git.add(str(solution_file))
            repo.git.add(str(yml_file))
            repo.git.add(str(nested_file))
            repo.git.add(str(cover_file))
            repo.git.commit("-m", "deploy commit")

        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))
        zenodo_manager = EmptyTestClass()
        deposit = self._create_mock_deposit(
            deposit_id="0", doi="doi", conceptdoi="conceptdoi"
        )
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value=deposit)
        # Capture zip contents during upload (temp dir is cleaned after)
        import zipfile

        captured_zip_contents = []

        def capture_upload(deposit, file):
            if Path(file).name == "solution.zip":
                with zipfile.ZipFile(file) as zf:
                    captured_zip_contents.extend(zf.namelist())
            return deposit

        zenodo_upload_mock = MagicMock(side_effect=capture_upload)
        zenodo_manager.zenodo_upload = zenodo_upload_mock
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_upload("branch", None, None, None)

        uploaded_names = {
            Path(call[0][1]).name for call in zenodo_upload_mock.call_args_list
        }
        # solution.yml individually for metadata, solution.zip for full content
        self.assertIn("solution.yml", uploaded_names)
        self.assertIn("solution.zip", uploaded_names)

        # verify the zip contains the nested file with correct path
        self.assertTrue(
            any("Main.java" in name for name in captured_zip_contents),
            "Main.java not found in zip: %s" % captured_zip_contents,
        )
        self.assertTrue(
            any(
                "src/main/java/Main.java" in name.replace(os.sep, "/")
                for name in captured_zip_contents
            ),
            "Nested path not preserved in zip: %s" % captured_zip_contents,
        )
        force_remove(repo_dir)

    def test_zenodo_upload_writes_conceptdoi_to_yml(self):
        """conceptdoi from the deposit must end up in the solution.yml."""
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        deposit = self._create_mock_deposit(
            deposit_id="42",
            doi="10.5281/zenodo.5678",
            conceptdoi="10.5281/zenodo.1234",
        )

        zenodo_manager = EmptyTestClass()
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value=deposit)
        zenodo_manager.zenodo_upload = MagicMock()
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_upload(branch, None, None, None)

        yml_on_disk = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertEqual("10.5281/zenodo.5678", yml_on_disk["doi"])
        self.assertEqual("42", yml_on_disk["deposit_id"])
        self.assertEqual("10.5281/zenodo.1234", yml_on_disk["conceptdoi"])
        force_remove(repo_dir)

    def test_zenodo_upload_derives_conceptdoi_from_conceptrecid(self):
        """When conceptdoi is empty (draft), conceptdoi must be derived from conceptrecid."""
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        # Simulate a brand-new draft: conceptdoi="" but conceptrecid present
        deposit = self._create_mock_deposit(
            deposit_id="42",
            doi="10.5281/zenodo.5678",
            conceptdoi="",
            conceptrecid="9999",
        )

        zenodo_manager = EmptyTestClass()
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value=deposit)
        zenodo_manager.zenodo_upload = MagicMock()
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_upload(branch, None, None, None)

        yml_on_disk = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertEqual("10.5281/zenodo.9999", yml_on_disk["conceptdoi"])
        force_remove(repo_dir)

    def test_zenodo_upload_no_conceptdoi_when_nothing_available(self):
        """When neither conceptdoi nor conceptrecid is set, no conceptdoi must appear."""
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)
        release_manager._prepare_zenodo_arguments = MagicMock(return_value=(None, None))

        deposit = self._create_mock_deposit(
            deposit_id="42",
            doi="10.5281/zenodo.5678",
            conceptdoi=None,
            conceptrecid=None,
        )

        zenodo_manager = EmptyTestClass()
        zenodo_manager.zenodo_get_deposit = MagicMock(return_value=deposit)
        zenodo_manager.zenodo_upload = MagicMock()
        release_manager._get_zenodo_manager = MagicMock(return_value=zenodo_manager)

        release_manager.zenodo_upload(branch, None, None, None)

        yml_on_disk = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertNotIn("conceptdoi", yml_on_disk)
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # commit_changes
    # ------------------------------------------------------------------

    @patch("album.ci.controller.release_manager.add_files_commit_and_push")
    def test_commit_changes(self, mock_push):
        """commit_changes must include the solution.yml and solution files."""
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        release_manager.commit_changes(branch, "user", "email")

        mock_push.assert_called_once()
        committed = [str(p) for p in mock_push.call_args[0][1]]

        # the yml must be in the commit list
        self.assertTrue(
            any(str(yml_relative_path) in f for f in committed),
            "solution.yml not found in commit_files: %s" % committed,
        )
        # commit message
        self.assertIn("Prepared branch", mock_push.call_args[0][2])
        # push must be False
        self.assertFalse(mock_push.call_args[1]["push"])
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # merge
    # ------------------------------------------------------------------

    @patch("album.ci.controller.release_manager.assert_main_not_advanced")
    @patch("album.ci.controller.release_manager.add_files_commit_and_push")
    def test_merge_commit_files_include_yml(self, mock_push, mock_assert_main):
        """merge must commit the solution.yml alongside index files."""
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        # create the index files that merge expects on disk
        # (in the real CI these are written by update_index before merge)
        # we need to trigger the clone first via _open_repo, then create them
        with release_manager._open_repo():
            pass  # clones to catalog_path
        solution_list = catalog_path.joinpath(
            DefaultValues.catalog_solution_list_file_name.value
        )
        index_db = catalog_path.joinpath(DefaultValues.catalog_index_file_name.value)
        solution_list.touch()
        index_db.touch()

        release_manager.merge(
            branch,
            dry_run=True,
            push_option=None,
            ci_user_name="user",
            ci_user_email="email",
        )

        mock_push.assert_called_once()
        committed = [str(p) for p in mock_push.call_args[0][1]]

        # all three must be present
        self.assertTrue(
            any("solution.yml" in f for f in committed),
            "solution.yml not in commit_files: %s" % committed,
        )
        self.assertTrue(
            any(
                DefaultValues.catalog_solution_list_file_name.value in f
                for f in committed
            ),
            "solution list not in commit_files: %s" % committed,
        )
        self.assertTrue(
            any(DefaultValues.catalog_index_file_name.value in f for f in committed),
            "index db not in commit_files: %s" % committed,
        )
        self.assertEqual(3, len(committed))
        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.assert_main_not_advanced")
    @patch("album.ci.controller.release_manager.add_files_commit_and_push")
    def test_merge_push_flag_respects_dry_run(self, mock_push, mock_assert_main):
        """dry_run=True → push=False, dry_run=False → push=True."""
        repo_dir, branch, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        with release_manager._open_repo():
            pass
        catalog_path.joinpath(
            DefaultValues.catalog_solution_list_file_name.value
        ).touch()
        catalog_path.joinpath(DefaultValues.catalog_index_file_name.value).touch()

        release_manager.merge(
            branch,
            dry_run=True,
            push_option=None,
            ci_user_name="u",
            ci_user_email="e",
        )
        self.assertFalse(mock_push.call_args[1]["push"])

        mock_push.reset_mock()

        release_manager.merge(
            branch,
            dry_run=False,
            push_option=None,
            ci_user_name="u",
            ci_user_email="e",
        )
        self.assertTrue(mock_push.call_args[1]["push"])
        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.assert_main_not_advanced")
    @patch("album.ci.controller.release_manager.add_files_commit_and_push")
    def test_merge_passes_allow_empty(self, mock_push, mock_assert_main):
        """merge must pass allow_empty=True so it tolerates no-change pushes."""
        repo_dir, branch, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        with release_manager._open_repo():
            pass
        catalog_path.joinpath(
            DefaultValues.catalog_solution_list_file_name.value
        ).touch()
        catalog_path.joinpath(DefaultValues.catalog_index_file_name.value).touch()

        release_manager.merge(
            branch,
            dry_run=True,
            push_option=None,
            ci_user_name="u",
            ci_user_email="e",
        )
        self.assertTrue(mock_push.call_args[1]["allow_empty"])
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # update_index
    # ------------------------------------------------------------------

    @patch("album.ci.controller.release_manager.retrieve_index_files_from_src")
    def test_update_index_writes_doi_and_deposit_id_to_yml(self, mock_retrieve_index):
        """update_index must write doi and deposit_id into the solution.yml."""
        # mock: return a non-existent path so the "not downloadable" branch is taken
        mock_retrieve_index.return_value = (Path("/does/not/exist.db"), Path("/x"))

        repo_dir, branch, yml_relative_path, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        # update_index calls load_catalog_index — stub it out
        release_manager.album_instance.load_catalog_index = MagicMock()

        # stub the catalog index so update/save/export succeed
        mock_index = MagicMock()
        release_manager.catalog._catalog_index = mock_index

        release_manager.update_index(branch, doi="10.5281/zenodo.5678", deposit_id="42")

        yml_on_disk = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertEqual("10.5281/zenodo.5678", yml_on_disk["doi"])
        self.assertEqual("42", yml_on_disk["deposit_id"])

        # index must have been updated and saved
        mock_index.update.assert_called_once()
        mock_index.save.assert_called_once()
        mock_index.export.assert_called_once()
        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.retrieve_index_files_from_src")
    def test_update_index_without_doi(self, mock_retrieve_index):
        """update_index with empty doi/deposit_id must not alter yml."""
        mock_retrieve_index.return_value = (Path("/does/not/exist.db"), Path("/x"))

        yml_input = {"group": "group", "name": "name", "version": "0.1.0"}
        repo_dir, branch, yml_relative_path, _ = self._create_source_repo(yml_input)
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        release_manager.album_instance.load_catalog_index = MagicMock()
        mock_index = MagicMock()
        release_manager.catalog._catalog_index = mock_index

        release_manager.update_index(branch, doi="", deposit_id="")

        yml_on_disk = get_dict_from_yml(catalog_path.joinpath(yml_relative_path))
        self.assertNotIn("doi", yml_on_disk)
        self.assertNotIn("deposit_id", yml_on_disk)

        # index update must still be called
        mock_index.update.assert_called_once()
        force_remove(repo_dir)

    # ------------------------------------------------------------------
    # merge — assert_main_not_advanced guard
    # ------------------------------------------------------------------

    @patch("album.ci.controller.release_manager.assert_main_not_advanced")
    @patch("album.ci.controller.release_manager.add_files_commit_and_push")
    def test_merge_calls_assert_main_not_advanced(self, mock_push, mock_assert_main):
        """merge must call assert_main_not_advanced to guard against races."""
        repo_dir, branch, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        with release_manager._open_repo():
            pass
        catalog_path.joinpath(
            DefaultValues.catalog_solution_list_file_name.value
        ).touch()
        catalog_path.joinpath(DefaultValues.catalog_index_file_name.value).touch()

        release_manager.merge(
            branch,
            dry_run=True,
            push_option=None,
            ci_user_name="u",
            ci_user_email="e",
        )

        mock_assert_main.assert_called_once()
        # first arg is the repo object, second is the catalog's main branch
        call_args = mock_assert_main.call_args[0]
        self.assertEqual(release_manager.catalog.branch_name(), call_args[1])
        force_remove(repo_dir)

    @patch("album.ci.controller.release_manager.add_files_commit_and_push")
    def test_merge_fails_when_main_advanced(self, mock_push):
        """merge must fail if assert_main_not_advanced raises RuntimeError."""
        repo_dir, branch, _, _ = self._create_source_repo()
        release_manager, catalog_path = self._create_release_manager(repo_dir)

        with release_manager._open_repo():
            pass
        catalog_path.joinpath(
            DefaultValues.catalog_solution_list_file_name.value
        ).touch()
        catalog_path.joinpath(DefaultValues.catalog_index_file_name.value).touch()

        with patch(
            "album.ci.controller.release_manager.assert_main_not_advanced",
            side_effect=RuntimeError("Main branch has advanced"),
        ):
            with self.assertRaises(RuntimeError):
                release_manager.merge(
                    branch,
                    dry_run=True,
                    push_option=None,
                    ci_user_name="u",
                    ci_user_email="e",
                )

        # add_files_commit_and_push must NOT have been called
        mock_push.assert_not_called()
        force_remove(repo_dir)
