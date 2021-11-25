import contextlib
import io
import json
import sys
import unittest

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationClone(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_index(self):
        sys.argv = ["", "index"]

        # run
        self.assertIsNone(main())

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn('name: catalog_local', self.captured_output.getvalue())

    def test_index_json(self):
        sys.argv = ["", "index", "--json"]

        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            self.assertIsNone(main())

        self.assertNotIn('ERROR', self.captured_output.getvalue())
        index_dict = json.loads(stdout_content.getvalue())
        self.assertIsNotNone(index_dict)
        self.assertIsNotNone(index_dict['catalogs'])
        self.assertEqual(2, len(index_dict['catalogs']))


if __name__ == '__main__':
    unittest.main()
