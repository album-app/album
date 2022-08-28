import contextlib
import io
import json
import sys
from unittest.mock import patch

from album.argument_parsing import main
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationCommandline(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_album_instance()

    def tearDown(self) -> None:
        super().tearDown()

    @patch("album.api.Album.load_or_create_collection")
    def test_mismatching_args(self, load_or_create_mock):
        sys.argv = ["", "--versn"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(1).code, e.exception.code)
        self.assertIn(
            "Invalid argument(s): ['--versn']", self.captured_output.getvalue()
        )
        load_or_create_mock.assert_not_called()

    @patch("album.api.Album.load_or_create_collection")
    @patch("album.core.controller.run_manager.RunManager.run")
    def test_run(self, run_mock, load_or_create_mock):
        sys.argv = ["", "run", "testpath"]
        self.assertIsNone(main())
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        run_mock.assert_called_once()
        load_or_create_mock.assert_called_once()

    @patch("album.api.Album.load_or_create_collection")
    @patch("album.core.controller.test_manager.TestManager.test")
    def test_test(self, test_mock, load_or_create_mock):
        sys.argv = ["", "test", "testpath"]
        self.assertIsNone(main())
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        test_mock.assert_called_once()
        load_or_create_mock.assert_called_once()

    @patch("album.api.Album.load_or_create_collection")
    @patch("album.core.controller.install_manager.InstallManager.install")
    def test_install(self, install_mock, load_or_create_mock):
        sys.argv = ["", "install", "testpath"]
        self.assertIsNone(main())
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        install_mock.assert_called_once()
        load_or_create_mock.assert_called_once()

    @patch("album.api.Album.load_or_create_collection")
    def test_search_no_keyword(self, _):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_filled_index(self):
        # populate tmp_index!
        h = self.album.load(self.get_test_solution_path())
        h.setup().description = "keyword1"
        local_catalog = (
            self.album._controller.collection_manager().catalogs().get_cache_catalog()
        )
        self.album._controller.collection_manager().solutions().add_to_cache_catalog(
            h, self.get_test_solution_path()
        )

        self.assertEqual(
            1,
            len(
                self.album._controller.collection_manager()
                .get_collection_index()
                .get_solutions_by_catalog(local_catalog.catalog_id())
            ),
        )

        # define and run search
        sys.argv = ["", "search", "keyword"]
        self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output.getvalue())

        # check output to have found the solution behind keyword1
        self.assertIn(
            "%s:%s:%s:%s"
            % (
                local_catalog.name(),
                h.coordinates().group(),
                h.coordinates().name(),
                h.coordinates().version(),
            ),
            self.captured_output.getvalue(),
        )

    def test_search_as_json(self):
        # populate tmp_index!
        h = self.album.load(self.get_test_solution_path())
        h.setup().description = "keyword1"
        local_catalog = (
            self.album._controller.collection_manager().catalogs().get_cache_catalog()
        )
        self.album._controller.collection_manager().solutions().add_to_cache_catalog(
            h, self.get_test_solution_path()
        )

        self.assertEqual(
            1,
            len(
                self.album._controller.collection_manager()
                .get_collection_index()
                .get_solutions_by_catalog(local_catalog.catalog_id())
            ),
        )

        # capture stdout
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            # define and run search
            sys.argv = ["", "search", "keyword1", "--json"]
            self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output.getvalue())
        # check output to have found the solution behind keyword1
        self.assertEqual(
            [["cache_catalog:group:name:0.1.0", 1]], json.loads(f.getvalue())
        )

    def test_test_not_installed(self):
        sys.argv = [
            "",
            "test",
            self.get_test_solution_path("solution0_dummy_no_routines.py"),
        ]

        # run
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertTrue(isinstance(e.exception.code, LookupError))

        self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("Solution not found", e.exception.code.args[0])

    def test_remove_solution_not_installed(self):
        sys.argv = ["", "uninstall", self.get_test_solution_path()]

        with self.assertRaises(SystemExit) as e:
            main()
        self.assertTrue(isinstance(e.exception.code, LookupError))

        self.assertIn("ERROR", self.captured_output.getvalue())
        self.assertIn("Solution not found", e.exception.code.args[0])

    def test_info(self):
        self.fake_install(
            self.get_test_solution_path("solution0_dummy_no_routines.py"),
            create_environment=False,
        )

        # run
        sys.argv = [
            "",
            "info",
            self.get_test_solution_path("solution0_dummy_no_routines.py"),
        ]
        self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertIn(
            "--testArg1: testArg1Description", self.captured_output.getvalue()
        )

    def test_info_json(self):
        self.fake_install(self.get_test_solution_path(), create_environment=False)

        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            # define and run search
            sys.argv = ["", "info", self.get_test_solution_path(), "--json"]
            self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertEqual(
            {
                "group": "group",
                "name": "name",
                "title": "name",
                "version": "0.1.0",
                "doi": "a/doi",
                "description": "A description",
                "solution_creators": ["Me"],
                "cite": [],
                "acknowledgement": "Hi mom",
                "tags": ["tag1", "tag2"],
                "license": "license",
                "covers": [],
                "album_api_version": "0.5.1",
                "args": [
                    {
                        "name": "testArg1",
                        "description": "testArg1Description",
                        "type": "string",
                        "default": "defaultValue",
                    }
                ],
            },
            json.loads(stdout_content.getvalue()),
        )

    def test_update_json(self):
        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            # define and run search
            sys.argv = ["", "update", "--catalog", "non-existing-catalog"]
            with self.assertRaises(SystemExit) as e:
                main()
            self.assertTrue(isinstance(e.exception.code, LookupError))

    def test_index(self):
        sys.argv = ["", "index"]

        # run
        self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output.getvalue())
        self.assertIn("name: cache_catalog", self.captured_output.getvalue())

    def test_index_json(self):
        sys.argv = ["", "index", "--json"]

        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            self.assertIsNone(main())

        self.assertNotIn("ERROR", self.captured_output.getvalue())
        index_dict = json.loads(stdout_content.getvalue())
        self.assertIsNotNone(index_dict)
        self.assertIsNotNone(index_dict["catalogs"])
        self.assertEqual(1, len(index_dict["catalogs"]))

    @patch("album.core.controller.conda_manager.CondaManager.get_environment_path")
    def test_run_sad_solution(self, get_environment_path):
        get_environment_path.return_value = (
            self.album._controller.environment_manager()
            .get_conda_manager()
            .get_active_environment_path()
        )
        solution_path = self.get_test_solution_path("solution9_throws_exception.py")
        self.fake_install(solution_path, create_environment=False)
        sys.argv = ["", "run", solution_path]

        # run
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEquals(1, e.exception.code)

    @patch("album.core.controller.conda_manager.CondaManager.get_environment_path")
    def test_run_album_throwing_error_solution(self, get_environment_path):
        get_environment_path.return_value = (
            self.album._controller.environment_manager()
            .get_conda_manager()
            .get_active_environment_path()
        )
        solution_path = str(
            self.get_test_solution_path("solution15_album_running_faulty_solution.py")
        )
        self.fake_install(solution_path, create_environment=False)

        sys.argv = ["", "run", solution_path, "--log", "DEBUG"]

        # run
        with self.assertRaises(SystemExit) as e:
            main()
        print(self.captured_output.getvalue())
        self.assertEqual(1, e.exception.code)
        # print(self.captured_output.getvalue())
        self.assertIn("INFO ~ print something", self.captured_output.getvalue())
        self.assertIn("INFO ~ logging info", self.captured_output.getvalue())
        self.assertIn("WARNING ~ logging warning", self.captured_output.getvalue())
        self.assertIn("ERROR ~ logging error", self.captured_output.getvalue())
        self.assertIn(
            "INFO ~~~ album in album: print something", self.captured_output.getvalue()
        )
        self.assertIn(
            "INFO ~~~ album in album: logging info", self.captured_output.getvalue()
        )
        self.assertIn(
            "WARNING ~~~ album in album: logging warning",
            self.captured_output.getvalue(),
        )
        self.assertIn(
            "ERROR ~~~ album in album: logging error", self.captured_output.getvalue()
        )
        self.assertIn(
            "INFO ~~~ RuntimeError: Error in run method",
            self.captured_output.getvalue(),
        )
