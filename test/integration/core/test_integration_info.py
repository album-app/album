import contextlib
import io
import json
import sys
import unittest

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTest(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_info(self):
        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"), create_environment=False)

        # run
        sys.argv = ["", "info", self.get_test_solution_path("solution0_dummy_no_routines.py")]
        self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output)
        self.assertIn("--testArg1: testArg1Description", self.captured_output.getvalue())

    def test_info_json(self):
        self.fake_install(self.get_test_solution_path("solution0_dummy_no_routines.py"), create_environment=False)

        # run
        stdout_content = io.StringIO()
        with contextlib.redirect_stdout(stdout_content):
            # define and run search
            sys.argv = ["", "info", self.get_test_solution_path("solution0_dummy_no_routines.py"), "--json"]
            self.assertIsNone(main())

        # assert
        self.assertNotIn("ERROR", self.captured_output)
        self.assertEqual({
            "args": [
                {
                    "description": "testArg1Description",
                    "name": "testArg1"
                }
            ],
            "authors": [],
            "cite": [],
            "covers": [],
            "description": "",
            "documentation": [],
            "acknowledgement": "",
            "group": "group",
            "license": "license",
            "album_version": "0.1.1",
            "album_api_version": "0.1.1",
            "name": "name",
            "tags": [],
            "timestamp": "",
            "title": "name",
            "version": "0.1.0"
        }, json.loads(stdout_content.getvalue()))


if __name__ == '__main__':
    unittest.main()
