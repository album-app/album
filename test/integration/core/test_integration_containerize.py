import sys
import unittest

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationContainerize(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_containerize(self):
        sys.argv = ["", "containerize", self.get_test_solution_path()]
        self.assertIsNone(main())


if __name__ == '__main__':
    unittest.main()
