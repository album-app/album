import importlib
import unittest
from importlib.metadata import PackageNotFoundError, metadata, version
from unittest.mock import patch

import album.ci
import album.core
from album.core.model.default_values import DefaultValues


class TestCoreMetadata(unittest.TestCase):
    """album's version and authors are only written down in pyproject.toml."""

    def test_version_is_the_installed_version(self):
        self.assertEqual(version("album"), album.core.__version__)

    def test_author_and_email_are_the_installed_authors(self):
        installed = metadata("album")
        authors = ", ".join(
            (installed.get_all("Author-email") or [])
            + (installed.get_all("Author") or [])
        )
        self.assertTrue(album.core.__author__)
        self.assertTrue(album.core.__email__)
        for name in album.core.__author__.split(", "):
            self.assertIn(name, authors)
        for email in album.core.__email__.split(", "):
            self.assertIn(email, authors)

    def test_contacts(self):
        # the way setuptools writes authors with an email to the "Author-email" field
        self.assertEqual(
            [
                ("Doe, Jane", "jane@example.org"),
                ("John Doe", "john@example.org"),
                ("", "team@example.org"),
            ],
            album.core._contacts(
                [
                    '"Doe, Jane" <jane@example.org>, John Doe <john@example.org>, team@example.org'
                ]
            ),
        )
        self.assertEqual([], album.core._contacts([]))

    def test_not_installed(self):
        try:
            with patch(
                "importlib.metadata.metadata",
                side_effect=PackageNotFoundError("album"),
            ):
                importlib.reload(album.core)
            self.assertEqual("unknown", album.core.__version__)
            self.assertEqual("", album.core.__author__)
            self.assertEqual("", album.core.__email__)
        finally:
            importlib.reload(album.core)
        self.assertEqual(version("album"), album.core.__version__)

    def test_catalog_admin_has_the_album_version(self):
        self.assertEqual(album.core.__version__, album.ci.__version__)
        self.assertEqual(album.core.__author__, album.ci.__author__)
        self.assertEqual(album.core.__email__, album.ci.__email__)

    def test_catalog_git_email_is_one_address(self):
        # a git identity takes a single address, not the list of all authors
        self.assertNotIn(",", DefaultValues.catalog_git_email.value)
        self.assertEqual(
            album.core.__email__.split(", ")[0], DefaultValues.catalog_git_email.value
        )
