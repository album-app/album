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


if __name__ == '__main__':
    unittest.main()
