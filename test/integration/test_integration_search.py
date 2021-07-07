import sys
import sys
import unittest

from hips.argument_parsing import main
from hips.core import load
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

    def test_search_filled_index(self):
        # populate tmp_index!
        h = load(self.get_test_solution_path())
        h["description"] = "keyword1"
        d = h.get_hips_deploy_dict()
        self.test_catalog_collection.local_catalog.catalog_index.update(d)
        self.test_catalog_collection.local_catalog.catalog_index.save()

        self.assertEqual(1, len(self.test_catalog_collection.local_catalog))

        # define and run search
        sys.argv = ["", "search", "keyword1"]
        self.assertIsNone(main())

        # check output to have found the solution behind keyword1
        self.assertIn(
            '%s_%s_%s_%s' % (self.test_catalog_collection.local_catalog.id, h["group"], h["name"], h["version"]),
            self.captured_output.getvalue()
        )


if __name__ == '__main__':
    unittest.main()
