import unittest
from test.unit.test_unit_core_common import EmptyTestClass, TestUnitCoreCommon
from unittest.mock import MagicMock

from album.ci.controller.zenodo_manager import ZenodoManager
from album.ci.utils.zenodo_api import InvalidResponseStatusError


class TestZenodoManager(TestUnitCoreCommon):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:

        # setUp is pass (no album_controller), so skip the parent tearDown
        # that would try self.album_controller.close().
        pass

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_zenodo_manager_with_mock_query():
        """Create a ZenodoManager with a mocked query object."""
        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()
        return zm

    @staticmethod
    def _make_record(
        record_id="19553456", doi="10.5281/zenodo.19553456", submitted=True
    ):
        record = EmptyTestClass()
        record.id = record_id
        record.doi = doi
        record.submitted = submitted
        return record

    # ------------------------------------------------------------------
    # get_published_deposit — fallback chain
    # ------------------------------------------------------------------

    def test_get_published_deposit_uses_deposit_api_when_available(self):
        """get_published_deposit must return via the deposit API when it
        succeeds, without touching the records API."""
        zm = self._create_zenodo_manager_with_mock_query()

        deposit = self._make_record()
        zm.query.deposit_get.return_value = [deposit]

        result = zm.get_published_deposit("19553456")

        zm.query.deposit_get.assert_called_once_with("19553456")
        zm.query.records_get.assert_not_called()
        self.assertEqual("19553456", result.id)

    def test_get_published_deposit_falls_back_to_records_api(self):
        """get_published_deposit must fall back to the records API when the
        deposits API raises InvalidResponseStatusError (e.g. 404).

        Regression test for InvalidResponseStatusError formerly inheriting
        from BaseException — ``except Exception`` could not catch it, so
        the records API fallback was never reached.
        """
        zm = self._create_zenodo_manager_with_mock_query()

        # deposits API → 404
        zm.query.deposit_get.side_effect = InvalidResponseStatusError("NotFound")

        # records API direct lookup → published record found
        published_record = self._make_record()
        zm.query.records_get.return_value = [published_record]

        result = zm.get_published_deposit("19553456")

        zm.query.records_get.assert_called_once_with(record_id="19553456")
        self.assertIsNotNone(result)
        self.assertEqual("19553456", result.id)

    def test_get_published_deposit_falls_back_to_doi_search(self):
        """get_published_deposit must search by DOI when both the deposit API
        and the direct records API lookup return 404.

        This is the exact scenario from https://zenodo.org/records/19553456 :
        after Zenodo's migration to InvenioRDM, the numeric DOI suffix no
        longer matches the record's API PID, so both direct lookups fail.
        The search API (``/api/records?q=doi:"..."``) still finds the record
        because it does not use the PID resolver.
        """
        zm = self._create_zenodo_manager_with_mock_query()

        # deposit API → 404
        zm.query.deposit_get.side_effect = InvalidResponseStatusError("NotFound")

        # records API: direct lookup → 404, DOI search → found
        published_record = self._make_record()

        def records_get_side_effect(**kwargs):
            if "record_id" in kwargs and kwargs["record_id"]:
                raise InvalidResponseStatusError("NotFound")
            if "q" in kwargs and "doi:" in kwargs["q"]:
                return [published_record]
            raise InvalidResponseStatusError("NotFound")

        zm.query.records_get.side_effect = records_get_side_effect

        result = zm.get_published_deposit("19553456", doi="10.5281/zenodo.19553456")

        self.assertIsNotNone(result)
        self.assertEqual("19553456", result.id)

        # Verify the call sequence: direct lookup first, then DOI search
        zm.query.records_get.assert_any_call(record_id="19553456")
        zm.query.records_get.assert_any_call(q='doi:"10.5281/zenodo.19553456"')
        self.assertEqual(2, zm.query.records_get.call_count)

    def test_get_published_deposit_returns_none_when_all_fail(self):
        """get_published_deposit must return None (not raise) when the
        deposit API, direct records API, and DOI search all fail."""
        zm = self._create_zenodo_manager_with_mock_query()

        zm.query.deposit_get.side_effect = InvalidResponseStatusError("NotFound")
        zm.query.records_get.side_effect = InvalidResponseStatusError("NotFound")

        result = zm.get_published_deposit("00000", doi="10.5281/zenodo.00000")

        self.assertIsNone(result)
        # Should have tried: direct lookup + DOI search = 2 records_get calls
        self.assertEqual(2, zm.query.records_get.call_count)

    def test_get_published_deposit_skips_doi_search_when_no_doi(self):
        """When no DOI is provided, the DOI search fallback must be skipped."""
        zm = self._create_zenodo_manager_with_mock_query()

        zm.query.deposit_get.side_effect = InvalidResponseStatusError("NotFound")
        zm.query.records_get.side_effect = InvalidResponseStatusError("NotFound")

        result = zm.get_published_deposit("00000")  # no doi param

        self.assertIsNone(result)
        # Only the direct lookup — no DOI search
        zm.query.records_get.assert_called_once_with(record_id="00000")

    # ------------------------------------------------------------------
    # stubs for unimplemented tests
    # ------------------------------------------------------------------
    @unittest.skip("Needs to be implemented!")
    def test_zenodo_upload(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_zenodo_get_deposit(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test_zenodo_get_unpublished_deposit_by_id(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test__check_deposit(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test__zenodo_get_deposit_by_id(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test__zenodo_get_unpublished(self):
        # todo: implement!
        pass

    @unittest.skip("Needs to be implemented!")
    def test__zenodo_get_published(self):
        # todo: implement!
        pass
