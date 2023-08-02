import unittest

from album.core.utils.operations.url_operations import (
    is_url,
    is_git_ssh_address,
)
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestUrlOperations(TestUnitCoreCommon):
    def setUp(self) -> None:
        super().setUp()
        self.downloadable_url = "https://www.google.com/favicon.ico"
        self.html_url = "https://www.google.com/"
        self.wrong_url = "https://www.google.com/favicon.i"

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

    @unittest.skip("Needs to be implemented!")
    def test_download(self):
        # Todo: implement
        pass
