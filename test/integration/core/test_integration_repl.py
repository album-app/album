import sys
import unittest

from album.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationRepl(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_repl(self):
        # todo: proper implement
        sys.argv = ["", "repl", self.get_test_solution_path()]
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())


if __name__ == '__main__':
    unittest.main()
