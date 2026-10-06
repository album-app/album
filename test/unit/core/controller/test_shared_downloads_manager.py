import sys
import unittest
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import patch

from album.core.controller.shared_downloads_manager import DownloadManager


class TestDownloadManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def _resource(self, name, **kwargs):
        """Build a resource entry as it looks after the paths were resolved."""
        resource = {
            "url": "https://example.org/%s" % name,
            "name": name,
            "path": Path(self.tmp_dir.name),
        }
        resource.update(kwargs)
        return resource

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_with_hash(
        self, retrieve_mock, file_hash_mock
    ):
        # prepare
        target = Path(self.tmp_dir.name).joinpath("res_a")
        retrieve_mock.return_value = str(target)
        resources_dict = {"resources": {"a": self._resource("res_a", hash="md5:abc")}}

        # call
        DownloadManager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_called_once()
        self.assertEqual("md5:abc", retrieve_mock.call_args.kwargs["known_hash"])
        file_hash_mock.assert_not_called()
        logs = self.get_logs_as_string()
        self.assertIn("Downloaded a resource to %s" % target, logs)
        self.assertNotIn("has no hash provided", logs)

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_without_hash(
        self, retrieve_mock, file_hash_mock
    ):
        """A resource without a "hash" key is downloaded and its md5 is reported."""
        # prepare
        target = Path(self.tmp_dir.name).joinpath("res_a")
        retrieve_mock.return_value = str(target)
        file_hash_mock.return_value = "0123456789abcdef"
        resources_dict = {"resources": {"a": self._resource("res_a")}}

        # call - must not raise a KeyError for the missing hash
        DownloadManager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_called_once()
        self.assertIsNone(retrieve_mock.call_args.kwargs["known_hash"])
        file_hash_mock.assert_called_once_with(str(target), alg="md5")
        logs = self.get_logs_as_string()
        self.assertIn("Resource res_a has no hash provided", logs)
        self.assertIn("0123456789abcdef", logs)

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_download_fails(
        self, retrieve_mock, file_hash_mock
    ):
        """A failed download is logged as an error, the hash hint is skipped for
        it and the remaining resources are still processed."""
        # prepare
        target_b = Path(self.tmp_dir.name).joinpath("res_b")
        retrieve_mock.side_effect = [ConnectionError("no route to host"), str(target_b)]
        file_hash_mock.return_value = "0123456789abcdef"
        resources_dict = {
            "resources": {
                "a": self._resource("res_a"),  # no hash, download fails
                "b": self._resource("res_b"),  # no hash, download works
            }
        }

        # call - must not raise a TypeError from pooch.file_hash(None)
        DownloadManager._retrieve_resources_from_dict(resources_dict)

        # assert
        self.assertEqual(2, retrieve_mock.call_count)
        file_hash_mock.assert_called_once_with(str(target_b), alg="md5")
        logs = self.get_logs_as_string()
        self.assertIn("Failed to download resource res_a: no route to host", logs)
        self.assertNotIn("Downloaded a resource to None", logs)
        self.assertNotIn("Resource res_a has no hash provided", logs)
        self.assertIn("Downloaded a resource to %s" % target_b, logs)
        self.assertIn("Resource res_b has no hash provided", logs)

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_download_fails_hash_none(
        self, retrieve_mock, file_hash_mock
    ):
        """An empty "hash" entry and a failed download must not hash None."""
        # prepare
        retrieve_mock.side_effect = ConnectionError("no route to host")
        resources_dict = {"resources": {"a": self._resource("res_a", hash=None)}}

        # call - must not raise a TypeError from pooch.file_hash(None)
        DownloadManager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_called_once()
        file_hash_mock.assert_not_called()
        logs = self.get_logs_as_string()
        self.assertIn("Failed to download resource res_a: no route to host", logs)
        self.assertNotIn("Downloaded a resource to None", logs)
        self.assertNotIn("has no hash provided", logs)

    @patch("album.core.controller.shared_downloads_manager.pooch.file_hash")
    @patch("album.core.controller.shared_downloads_manager.pooch.retrieve")
    def test__retrieve_resources_from_dict_skips_other_os(
        self, retrieve_mock, file_hash_mock
    ):
        # prepare
        other_os = "not-" + sys.platform
        resources_dict = {"resources": {"a": self._resource("res_a", os=other_os)}}

        # call
        DownloadManager._retrieve_resources_from_dict(resources_dict)

        # assert
        retrieve_mock.assert_not_called()
        file_hash_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
