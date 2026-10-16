import argparse
import os
import sys
import tempfile
import unittest.mock
from argparse import Namespace
from unittest.mock import MagicMock, call, patch

from album import argument_parsing
from album.commandline import (
    add_catalog,
    clone,
    deploy,
    install,
    remove_catalog,
    repl,
    run,
    search,
    test,
    uninstall,
    upgrade_solutions,
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

    def test_index_all(self):
        parser = argument_parsing.create_parser()

        sys.argv = ["", "index"]
        self.assertFalse(parser.parse_known_args()[0].all)

        sys.argv = ["", "index", "--all"]
        self.assertTrue(parser.parse_known_args()[0].all)

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

    def test_deploy_force_deploy_flag(self):
        parser = argument_parsing.create_parser()

        # without the flag force_deploy must be off (matches Album.deploy default)
        sys.argv = ["", "deploy", "test/path", "catalog-name"]
        args = parser.parse_known_args()
        self.assertEqual(deploy, args[0].func)
        self.assertFalse(args[0].force_deploy)

        # the flag enables force deploy, as its help text says
        sys.argv = ["", "deploy", "test/path", "catalog-name", "--force-deploy"]
        args = parser.parse_known_args()
        self.assertEqual(deploy, args[0].func)
        self.assertTrue(args[0].force_deploy)

    def test_deploy_no_replicability_flag(self):
        parser = argument_parsing.create_parser()

        sys.argv = ["", "deploy", "test/path", "catalog-name"]
        args = parser.parse_known_args()
        self.assertFalse(args[0].no_replicability)

        sys.argv = ["", "deploy", "test/path", "catalog-name", "--no-replicability"]
        args = parser.parse_known_args()
        self.assertTrue(args[0].no_replicability)

    def test_abbreviated_options_are_passed_to_the_solution(self):
        parser = argument_parsing.create_parser()

        # an abbreviation of --json or --log belongs to the solution
        sys.argv = ["", "run", "test/path", "--js", "--lo", "DEBUG"]
        args = parser.parse_known_args()
        self.assertFalse(args[0].json)
        self.assertEqual(["--js", "--lo", "DEBUG"], args[1])

        # the full option is album's
        sys.argv = ["", "run", "test/path", "--json"]
        args = parser.parse_known_args()
        self.assertTrue(args[0].json)
        self.assertEqual([], args[1])

    def test_run_install_flag(self):
        parser = argument_parsing.create_parser()

        sys.argv = ["", "run", "test/path", "--name", "x"]
        args = parser.parse_known_args()
        self.assertFalse(args[0].install)

        # --install is album's, the rest belongs to the solution
        sys.argv = ["", "run", "test/path", "--install", "--name", "x"]
        args = parser.parse_known_args()
        self.assertTrue(args[0].install)
        self.assertEqual(["--name", "x"], args[1])

    def test_install_reinstall_flag(self):
        parser = argument_parsing.create_parser()

        sys.argv = ["", "install", "test/path"]
        self.assertFalse(parser.parse_known_args()[0].reinstall)

        sys.argv = ["", "install", "test/path", "--reinstall"]
        self.assertTrue(parser.parse_known_args()[0].reinstall)

    def test_upgrade_solutions_parser(self):
        # registered as an entry point in pyproject.toml, created here directly
        album_parser = argument_parsing.AlbumParser()
        argument_parsing.create_upgrade_solutions_parser(album_parser)

        sys.argv = ["", "upgrade-solutions"]
        args = album_parser.parser.parse_known_args()[0]
        self.assertEqual(upgrade_solutions, args.func)
        self.assertEqual([], args.solutions)
        self.assertFalse(args.dry_run)

        sys.argv = ["", "upgrade-solutions", "grp:a", "cat:grp:b:0.1.0", "--dry-run"]
        args = album_parser.parser.parse_known_args()[0]
        self.assertEqual(["grp:a", "cat:grp:b:0.1.0"], args.solutions)
        self.assertTrue(args.dry_run)

    def test_undeploy_takes_coordinates(self):
        parser = argument_parsing.create_parser()

        sys.argv = ["", "undeploy", "grp:name:0.1.0", "catalog-name"]
        args = parser.parse_known_args()
        self.assertEqual("grp:name:0.1.0", args[0].path)
        self.assertEqual("catalog-name", args[0].catalog)

        help_text = self._get_command_parser(parser, "undeploy").format_help()
        self.assertIn("group:name:version", help_text)
        self.assertNotIn("path for the solution file", help_text)

    def test_help_of_the_solution_argument(self):
        parser = argument_parsing.create_parser()

        for command in ["install", "run", "info", "test", "uninstall", "repl"]:
            help_text = self._get_command_parser(parser, command).format_help()
            self.assertIn("group:name:version", help_text, command)
            self.assertIn("DOI", help_text, command)

        self.assertIn(
            "folder", self._get_command_parser(parser, "deploy").format_help()
        )
        # --uninstall-deps is a flag, it takes no True or False
        self.assertNotIn(
            "True, False",
            self._get_command_parser(parser, "uninstall").format_help(),
        )

    @staticmethod
    def _get_command_parser(parser, name):
        subparsers = next(
            a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
        )
        return subparsers.choices[name]

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


class TestRunCommand(unittest.TestCase):
    def setUp(self):
        self.album_instance = MagicMock()
        self._argv = sys.argv
        # what argument parsing leaves for the solution
        sys.argv = ["", "--name", "x"]

    def tearDown(self):
        sys.argv = self._argv

    def test_run_install_missing(self):
        self.album_instance.is_installed.return_value = False

        run(self.album_instance, Namespace(path="grp:name:0.1.0", install=True))

        # installed first, then run with the solution arguments
        self.assertEqual(
            [
                call.is_installed("grp:name:0.1.0"),
                call.install("grp:name:0.1.0"),
                call.run("grp:name:0.1.0", argv=["", "--name", "x"]),
            ],
            self.album_instance.mock_calls,
        )

    def test_run_install_installed(self):
        self.album_instance.is_installed.return_value = True

        run(self.album_instance, Namespace(path="grp:name:0.1.0", install=True))

        self.album_instance.install.assert_not_called()
        self.album_instance.run.assert_called_once_with(
            "grp:name:0.1.0", argv=["", "--name", "x"]
        )

    def test_run_without_install(self):
        run(self.album_instance, Namespace(path="grp:name:0.1.0", install=False))

        # not even looked up: a solution that is not installed fails in run
        self.album_instance.is_installed.assert_not_called()
        self.album_instance.install.assert_not_called()
        self.album_instance.run.assert_called_once_with(
            "grp:name:0.1.0", argv=["", "--name", "x"]
        )


class TestInstallAndUpgradeCommands(unittest.TestCase):
    def setUp(self):
        self.album_instance = MagicMock()

    @staticmethod
    def _result(**changes):
        result = {
            "dry_run": False,
            "install": [],
            "uninstall": [],
            "keep": [],
            "unused": [],
            "failed": [],
        }
        result.update(changes)
        return result

    def test_install_reinstall(self):
        install(
            self.album_instance,
            Namespace(path="grp:name:0.1.0", allow_recursive=False, reinstall=True),
        )

        self.album_instance.install.assert_called_once_with(
            "grp:name:0.1.0", False, sys.argv, reinstall=True
        )

    def test_upgrade_solutions(self):
        self.album_instance.upgrade_solutions.return_value = self._result(
            install=["cat:grp:a:0.2.0"]
        )

        upgrade_solutions(
            self.album_instance,
            Namespace(solutions=["grp:a"], dry_run=True, json=False),
        )

        self.album_instance.upgrade_solutions.assert_called_once_with(
            ["grp:a"], dry_run=True
        )

    @patch("builtins.print")
    def test_upgrade_solutions_failed(self, print_mock):
        self.album_instance.upgrade_solutions.return_value = self._result(
            failed=[{"solution": "cat:grp:a:0.2.0", "error": "broken"}]
        )

        # the result is printed, then the command fails
        with self.assertRaises(RuntimeError) as e:
            upgrade_solutions(
                self.album_instance,
                Namespace(solutions=[], dry_run=False, json=True),
            )

        self.assertIn("cat:grp:a:0.2.0", str(e.exception))
        self.assertIn('"error": "broken"', print_mock.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
