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

    def test_get_published_deposit_falls_back_to_records_api(self):
        """get_published_deposit must fall back to the records API when the
        deposits API raises InvalidResponseStatusError (e.g. 404).

        This is the exact scenario from https://zenodo.org/records/19553456 :
        the deposit is published and visible via /api/records but the
        /api/deposit/depositions endpoint returns 404 for it.

        Regression test for InvalidResponseStatusError formerly inheriting
        from BaseException — ``except Exception`` could not catch it, so
        the records API fallback was never reached.
        """
        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()

        # deposits API → 404  (InvalidResponseStatusError is now Exception)
        zm.query.deposit_get.side_effect = InvalidResponseStatusError(
            "Error 'NotFound' occurred. See Log for detailed information!"
        )

        # records API → published deposit found
        published_record = EmptyTestClass()
        published_record.id = "19553456"
        published_record.doi = "10.5281/zenodo.19553456"
        published_record.submitted = True
        zm.query.records_get.return_value = [published_record]

        result = zm.get_published_deposit("19553456")

        # The records API must have been consulted
        zm.query.records_get.assert_called_once_with(record_id="19553456")
        # … and the published record must be returned
        self.assertIsNotNone(result)
        self.assertEqual("19553456", result.id)

    def test_get_published_deposit_returns_none_when_both_apis_fail(self):
        """get_published_deposit must return None (not raise) when both the
        deposits API and the records API fail."""
        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()

        zm.query.deposit_get.side_effect = InvalidResponseStatusError("NotFound")
        zm.query.records_get.side_effect = InvalidResponseStatusError("NotFound")

        result = zm.get_published_deposit("00000")

        self.assertIsNone(result)

    def test_get_published_deposit_uses_deposit_api_when_available(self):
        """get_published_deposit must return via the deposit API when it
        succeeds, without touching the records API."""
        zm = ZenodoManager.__new__(ZenodoManager)
        zm.query = MagicMock()

        deposit = EmptyTestClass()
        deposit.id = "19553456"
        deposit.submitted = True
        zm.query.deposit_get.return_value = [deposit]

        result = zm.get_published_deposit("19553456")

        zm.query.deposit_get.assert_called_once_with("19553456")
        zm.query.records_get.assert_not_called()
        self.assertEqual("19553456", result.id)

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
