import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock

from album.ci.argument_parsing import AlbumCIParser


class TestCiArgumentParsing(TestUnitCoreCommon):
    @unittest.skip("Needs to be implemented!")
    def test_main(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_parser(self):
        pass


class TestAlbumCIParser(TestUnitCoreCommon):
    @unittest.skip("Needs to be implemented!")
    def test__init__(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_parent_parser(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_parser(self):
        pass

    def test_create_catalog_command_parser(self):
        parser = AlbumCIParser().create_catalog_command_parser(
            "test-command", MagicMock(), "test help"
        )

        args = parser.parse_args(["name", "path", "src"])
        self.assertFalse(args.force_retrieve)

        args = parser.parse_args(["name", "path", "src", "--force-retrieve"])
        self.assertTrue(args.force_retrieve)

        # the flag takes no value, "--force-retrieve False" used to mean True
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["name", "path", "src", "--force-retrieve", "False"])

    @unittest.skip("Needs to be implemented!")
    def test_create_git_command_parser(self):
        pass

    @unittest.skip("Needs to be implemented!")
    def test_create_zenodo_command_parser(self):
        pass
