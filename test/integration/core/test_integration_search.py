import contextlib
import io
import json
import sys
import unittest

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationSearch(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_search_no_keyword(self):
        sys.argv = ["", "search"]
        with self.assertRaises(SystemExit) as e:
            main()
        self.assertEqual(SystemExit(2).code, e.exception.code)

    def test_search_emtpy_index(self):
        sys.argv = ["", "search", "keyword"]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())

    def test_search_filled_index(self):
        # populate tmp_index!
        h = self.album_instance.state_manager().load(self.get_test_solution_path())
        h.setup().description = "keyword1"
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        self.collection_manager.add_solution_to_local_catalog(h, self.get_test_solution_path())

        self.assertEqual(1, len(self.collection_manager.catalog_collection.get_solutions_by_catalog(local_catalog.catalog_id())))

        # define and run search
        sys.argv = ["", "search", "keyword1"]
        self.assertIsNone(main())

        self.assertNotIn('ERROR', self.captured_output.getvalue())

        # check output to have found the solution behind keyword1
        self.assertIn(
            '%s:%s:%s:%s' % (local_catalog.name(), h.coordinates().group(), h.coordinates().name(), h.coordinates().version()),
            self.captured_output.getvalue()
        )

    def test_search_as_json(self):
        # populate tmp_index!
        h = self.album_instance.state_manager().load(self.get_test_solution_path())
        h.setup().description = "keyword1"
        local_catalog = self.collection_manager.catalogs().get_local_catalog()
        self.collection_manager.add_solution_to_local_catalog(h, self.get_test_solution_path())

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


if __name__ == '__main__':
    unittest.main()
