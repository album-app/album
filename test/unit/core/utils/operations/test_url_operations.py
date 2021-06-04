import tempfile
import unittest


# todo: write unit
from pathlib import Path

from hips.core.utils.operations.url_operations import is_downloadable, download_resource, _request_get
from test.unit.test_common import TestHipsCommon


class TestUrlOperations(TestHipsCommon):

    def setUp(self) -> None:
        self.downloadable_url = "https://www.google.com/favicon.ico"
        self.html_url = "https://gitlab.com/"
        self.wrong_url = "https://www.google.com/favicon.i"

    def tearDown(self) -> None:
        super().tearDown()

    def test_is_downloadable_true(self):
        self.assertTrue(is_downloadable(self.downloadable_url))

    def test_is_downloadable_false(self):
        self.assertFalse(is_downloadable(self.html_url))
        self.assertFalse(is_downloadable(self.wrong_url))

    def test_download_resource(self):
        p = Path(self.tmp_dir.name).joinpath("tmp_download")

        r = download_resource(self.downloadable_url, p)

        self.assertEqual(p, r)
        self.assertTrue(p.is_file())
        self.assertTrue(p.stat().st_size > 0)

    def test_download_resource_fail(self):

        p = Path(self.tmp_dir.name).joinpath("tmp_download")

        with self.assertRaises(AssertionError) as context:
            r = download_resource(self.wrong_url, p)
            self.assertEqual(context.exception, "Resource \"%s\" not downloadable!" % self.downloadable_url)

    def test__request_get_ok(self):
        _request_get(self.downloadable_url)

    def test__request_get_failed(self):
        with self.assertRaises(ConnectionError) as context:
            _request_get(self.wrong_url)
            self.assertEqual(context.exception, "Could not connect to resource %s!" % self.wrong_url)
