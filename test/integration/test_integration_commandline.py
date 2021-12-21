import contextlib
import io
import json
import sys
import unittest
from unittest.mock import patch

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationCommandline(TestIntegrationCommon):

    @patch('album.api.Album.load_or_create_collection')
    @patch('album.commandline._resolve_installed')
    @patch('album.core.controller.run_manager.RunManager.run')
    def test_run(self, run_mock, resolve_mock, load_or_create_mock):
        sys.argv = ["", "run", "testpath"]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        resolve_mock.assert_called_once()
        run_mock.assert_called_once()
        load_or_create_mock.assert_called_once()

    @patch('album.api.Album.load_or_create_collection')
    @patch('album.commandline._resolve_installed')
    @patch('album.core.controller.test_manager.TestManager.test')
    def test_test(self, test_mock, resolve_mock, load_or_create_mock):
        sys.argv = ["", "test", "testpath"]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        resolve_mock.assert_called_once()
        test_mock.assert_called_once()
        load_or_create_mock.assert_called_once()

    @patch('album.api.Album.load_or_create_collection')
    @patch('album.commandline._resolve')
    @patch('album.core.controller.install_manager.InstallManager.install')
    def test_install(self, install_mock, resolve_mock, load_or_create_mock):
        sys.argv = ["", "install", "testpath"]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        resolve_mock.assert_called_once()
        install_mock.assert_called_once()
        load_or_create_mock.assert_called_once()

    @patch('album.api.Album.load_or_create_collection')
    def test_search_no_keyword(self, _):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_filled_index(self):
        self.init_collection()
        # populate tmp_index!
        h = self.album_instance.load(self.get_test_solution_path())
        h.setup().description = "keyword1"
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        self.collection_manager.solutions().add_to_local_catalog(h, self.get_test_solution_path())

        self.assertEqual(1, len(self.collection_manager.catalog_collection.get_solutions_by_catalog(local_catalog.catalog_id())))

        # define and run search
        sys.argv = ["", "search", "keyword"]
        self.assertIsNone(main())

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # check output to have found the solution behind keyword1
        self.assertIn(
            '%s:%s:%s:%s' % (local_catalog.name(), h.coordinates().group(), h.coordinates().name(), h.coordinates().version()),
            self.captured_output.getvalue()
        )

    def test_search_as_json(self):
        self.init_collection()
        # populate tmp_index!
        h = self.album_instance.load(self.get_test_solution_path())
        h.setup().description = "keyword1"
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        self.collection_manager.solutions().add_to_local_catalog(h, self.get_test_solution_path())

        self.assertEqual(1, len(self.collection_manager.catalog_collection.get_solutions_by_catalog(local_catalog.catalog_id())))

        # capture stdout
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            # define and run search
            sys.argv = ["", "search", "keyword1", "--json"]
            self.assertIsNone(main())

        self.assertNotIn('ERROR', self.captured_output.getvalue())
        # check output to have found the solution behind keyword1
        self.assertEqual(
            [['catalog_local:group:name:0.1.0', 1]],
            json.loads(f.getvalue())
        )

    def test_test_not_installed(self):
        sys.argv = ["", "test", self.get_test_solution_path("solution0_dummy_no_routines.py")]

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
        self.init_collection()
        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"), create_environment=False)

        # run
        sys.argv = ["", "info", self.get_test_solution_path("solution0_dummy_no_routines.py")]
        self.assertIsNone(main())

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn("--testArg1: testArg1Description", self.captured_output.getvalue())

    def test_info_json(self):
        self.init_collection()
        self.fake_install(self.get_test_solution_path(), create_environment=False)

        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            # define and run search
            sys.argv = ["", "info", self.get_test_solution_path(), "--json"]
            self.assertIsNone(main())

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertEqual({
            'group': 'group',
            'name': 'name',
            'title': 'name',
            'version': '0.1.0',
            'doi': 'a/doi',
            'description': 'A description',
            'authors': ['Me'],
            'cite': [],
            'acknowledgement': 'Hi mom',
            'tags': ['tag1', 'tag2'],
            'license': 'license',
            'documentation': ['file.md'],
            'covers': [],
            'album_api_version': '0.2.1',
            'args': [
                {
                    'name': 'testArg1',
                    'description': 'testArg1Description',
                    'type': 'string'
                }
            ]
        }, json.loads(stdout_content.getvalue()))

    def test_index(self):
        self.init_collection()
        sys.argv = ["", "index"]

        # run
        self.assertIsNone(main())

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn('name: catalog_local', self.captured_output.getvalue())

    def test_index_json(self):
        self.init_collection()
        sys.argv = ["", "index", "--json"]

        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            self.assertIsNone(main())

        self.assertNotIn('ERROR', self.captured_output.getvalue())
        index_dict = json.loads(stdout_content.getvalue())
        self.assertIsNotNone(index_dict)
        self.assertIsNotNone(index_dict['catalogs'])
        self.assertEqual(1, len(index_dict['catalogs']))

if __name__ == '__main__':
    unittest.main()
