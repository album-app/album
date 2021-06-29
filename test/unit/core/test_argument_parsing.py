import os
import sys
import tempfile
import unittest.mock
from unittest.mock import patch

from hips import argument_parsing

# the functions to call. Caution: do not import as module!
from hips.core.commandline import containerize, deploy, install, remove, repl, run, search, tutorial, test, start_server, \
    add_catalog, remove_catalog


class TestArgumentParsing(unittest.TestCase):

    def setUp(self):
        pass

    @patch('hips.argument_parsing.__run_subcommand', return_value=True)
    def test_run(self, _):
        fp = tempfile.NamedTemporaryFile(mode='w+', delete=False)
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

    def test_run_non_existing_file(self):
        sys.argv = ["", "run", "test/path"]
        with self.assertRaises(ValueError):
            argument_parsing.main()

    def test_create_parser(self):
        parser = argument_parsing.create_parser()

        # check parsing of subcommands
        self.assertSubcommandParsed(parser, "search", search, "keyword")
        self.assertSubcommandParsed(parser, "server", start_server, "1234")
        self.assertSubcommandWithFileArgParsed(parser, "run", run)
        self.assertSubcommandWithFileArgParsed(parser, "deploy", deploy)
        self.assertSubcommandWithFileArgParsed(parser, "repl", repl)
        self.assertSubcommandWithFileArgParsed(parser, "install", install)
        self.assertSubcommandWithFileArgParsed(parser, "remove", remove)
        self.assertSubcommandWithFileArgParsed(parser, "containerize", containerize)
        self.assertSubcommandWithFileArgParsed(parser, "tutorial", tutorial)
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

    def assertSubcommandWithFileArgParsed(self, parser, name, method):
        sys.argv = ["", name, "test/path"]
        args = parser.parse_known_args()
        self.assertEqual(method, args[0].func)


if __name__ == '__main__':
    unittest.main()
