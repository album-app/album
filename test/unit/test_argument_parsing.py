import os
import sys
import tempfile
import unittest.mock
from unittest.mock import patch

from album import argument_parsing
from album.commandline import (
    search,
    remove_catalog,
    add_catalog,
    uninstall,
    install,
    repl,
    deploy,
    run,
    test,
    clone,
)


class TestArgumentParsing(unittest.TestCase):
    @patch("album.argument_parsing.__run_subcommand", return_value=True)
    def test_run(self, _):
        fp = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        fp.close()

        try:
            sys.argv = ["", "run", fp.name]
            self.assertIsNone(argument_parsing.main())
        finally:
            os.remove(fp.name)

    def test_run_no_args(self):
        sys.argv = ["", "run"]
        with self.assertRaises(SystemExit) as e:
            argument_parsing.main()

        self.assertEqual(e.exception.code, 2)

    def test_create_parser(self):
        parser = argument_parsing.create_parser()

        # check parsing of subcommands
        self.assertSubcommandParsed(parser, "search", search, "keyword")
        self.assertSubcommandWithFileArgParsed(parser, "run", run)
        self.assertSubcommandWithFileArgParsed(
            parser, "deploy", deploy, ["catalog-name"]
        )
        self.assertSubcommandWithFileArgParsed(
            parser, "clone", clone, ["target-dir", "name"]
        )
        self.assertSubcommandWithFileArgParsed(parser, "repl", repl)
        self.assertSubcommandWithFileArgParsed(parser, "install", install)
        self.assertSubcommandWithFileArgParsed(parser, "uninstall", uninstall)
        self.assertSubcommandWithFileArgParsed(parser, "test", test)
        self.assertSubcommandWithFileArgParsed(parser, "add-catalog", add_catalog)
        self.assertSubcommandWithFileArgParsed(parser, "remove-catalog", remove_catalog)

        # check parsing of additional arguments
        sys.argv = ["", "run", "test/path", "--input", "/other/path"]
        args = parser.parse_known_args()
        self.assertEqual(["--input", "/other/path"], args[1])

    def assertSubcommandParsed(self, parser, name, method, arguments=None):
        sys.argv = ["", name]
        if arguments:
            sys.argv = sys.argv + [arguments]
        args = parser.parse_known_args()
        self.assertEqual(method, args[0].func)

    def assertSubcommandWithFileArgParsed(
        self, parser, name, method, additional_args=None
    ):
        if additional_args is None:
            additional_args = []
        sys.argv = ["", name, "test/path"] + additional_args
        args = parser.parse_known_args()
        self.assertEqual(method, args[0].func)


if __name__ == "__main__":
    unittest.main()
