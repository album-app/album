import sys
import unittest

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTutorial(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_tutorial(self):
        sys.argv = ["", "tutorial", self.get_test_solution_path()]
        self.assertIsNone(main())


if __name__ == '__main__':
    unittest.main()
