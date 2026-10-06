import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from album.core.utils.operations.url_operations import (
    download,
    is_git_ssh_address,
    is_url,
)
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestUrlOperations(TestUnitCoreCommon):
    def setUp(self) -> None:
        super().setUp()
        self.downloadable_url = "https://www.google.com/favicon.ico"
        self.html_url = "https://www.google.com/"
        self.wrong_url = "https://www.google.com/favicon.i"
        self.download_base = Path(self.tmp_dir.name).joinpath("download")

    def tearDown(self) -> None:
        super().tearDown()

    def test_is_url(self):
        u1 = is_url("http://abc.de")
        u2 = is_url("https://abc.de:8080/")
        u3 = is_url("ftp://abc.de")
        u4 = is_url("ftp://abc.de:1234")
        u5 = is_url("not a url")
        u6 = is_url("/tmp/test")

        self.assertTrue(all([u1, u2, u3, u4]))
        self.assertFalse(all([u5, u6]))

    def test_is_git_ssh_address(self):
        u1 = is_git_ssh_address("user@host:project")
        u2 = is_git_ssh_address("ssh://user@host:project")
        u3 = is_git_ssh_address("git@host:project")
        u4 = is_git_ssh_address("git@host:project.git")
        u5 = is_git_ssh_address("git@host:project.git/")
        u6 = is_git_ssh_address("git@host:project.git/branch")
        u7 = is_git_ssh_address("git@host:project.git/branch/")
        u8 = is_git_ssh_address("git@host:project.git/branch/branch")

        u9 = is_git_ssh_address("not a git ssh address")
        u10 = is_git_ssh_address("/local/path/to/project")
        u11 = is_git_ssh_address("http://abc.de")
        u12 = is_git_ssh_address("email@adress.com")

        self.assertTrue(all([u1, u2, u3, u4, u5, u6, u7, u8]))
        self.assertFalse(all([u9, u10, u11, u12]))

    @staticmethod
    def _mock_session(status_code: int, content: bytes) -> MagicMock:
        """Build a session mock answering every GET with the given response."""
        response = MagicMock()
        response.status_code = status_code
        response.content = content
        session = MagicMock()
        session.__enter__.return_value = session
        session.get.return_value = response
        return session

    def _download(self, session: MagicMock) -> tuple[Path, list[int]]:
        """Run download() against a session mock, recording the fds from mkstemp."""
        real_mkstemp = tempfile.mkstemp
        fds = []

        def recording_mkstemp(*args, **kwargs):
            fd, name = real_mkstemp(*args, **kwargs)
            fds.append(fd)
            return fd, name

        with patch(
            "album.core.utils.operations.url_operations._get_session",
            return_value=session,
        ):
            with patch(
                "album.core.utils.operations.url_operations.tempfile.mkstemp",
                side_effect=recording_mkstemp,
            ):
                path = download(self.downloadable_url, str(self.download_base))

        return path, fds

    def _assert_closed(self, fds: list[int]) -> None:
        for fd in fds:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_download(self):
        content = b"print('hello')"
        session = self._mock_session(200, content)

        path, fds = self._download(session)

        session.get.assert_called_once_with(
            self.downloadable_url, allow_redirects=True, stream=True
        )
        self.assertEqual(self.download_base, path.parent)
        self.assertNotEqual(".zip", path.suffix)
        self.assertEqual(content, path.read_bytes())
        self.assertEqual(1, len(fds))
        self._assert_closed(fds)
        # fails on Windows while a descriptor of the file is still open
        path.unlink()
        self.assertFalse(path.exists())

    def test_download_zip(self):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            zip_file.writestr("solution.py", "print('hello')")
        session = self._mock_session(200, zip_buffer.getvalue())

        path, fds = self._download(session)

        self.assertEqual(self.download_base, path.parent)
        self.assertEqual(".zip", path.suffix)
        self.assertTrue(zipfile.is_zipfile(path))
        self.assertEqual(2, len(fds))
        self._assert_closed(fds)
        # both temporary files, the plain one and its ".zip" copy, must be deletable
        for tmp_file in self.download_base.iterdir():
            tmp_file.unlink()
        self.assertEqual([], list(self.download_base.iterdir()))

    def test_download_not_found(self):
        session = self._mock_session(404, b"<html>Not Found</html>")

        with self.assertRaises(ConnectionError):
            self._download(session)

        self.assertEqual([], list(self.download_base.iterdir()))


if __name__ == "__main__":
    unittest.main()
