import os
import sys
import tempfile
import unittest.mock
from unittest.mock import patch

from hips import cmdline

# the functions to call. Caution: do not import as module!
from hips.core.deploy import deploy
from hips.core.install import install
from hips.core.containerize import containerize
from hips.core.tutorial import tutorial
from hips.core.remove import remove
from hips.core.repl import repl
from hips.core.run import run
from hips.core.search import search


class TestCommandLine(unittest.TestCase):

    def setUp(self):
        pass

    @patch('hips.cmdline.__run_subcommand', return_value=True)
    def test_run(self, _):
        fd, path = tempfile.mkstemp()
        try:
            sys.argv = ["", "run", path]
            self.assertIsNone(cmdline.main())
        finally:
            os.remove(path)

    def test_run_no_args(self):
        sys.argv = ["", "run"]
        with self.assertRaises(SystemExit) as e:
            cmdline.main()

        self.assertEqual(e.exception.code, 2)

    def test_run_non_existing_file(self):
        sys.argv = ["", "run", "test/path"]
        with self.assertRaises(ValueError):
            cmdline.main()

    def test_create_parser(self):
        parser = cmdline.create_parser()

        # check parsing of subcommands
        self.assertSubcommandParsed(parser, "search", search, "keyword")
        self.assertSubcommandWithFileArgParsed(parser, "run", run)
        self.assertSubcommandWithFileArgParsed(parser, "deploy", deploy)
        self.assertSubcommandWithFileArgParsed(parser, "repl", repl)
        self.assertSubcommandWithFileArgParsed(parser, "install", install)
        self.assertSubcommandWithFileArgParsed(parser, "remove", remove)
        self.assertSubcommandWithFileArgParsed(parser, "containerize", containerize)
        self.assertSubcommandWithFileArgParsed(parser, "tutorial", tutorial)

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
