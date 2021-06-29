import sys
import unittest

from hips.argument_parsing import main
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationDeploy(TestIntegrationCommon):

    def tearDown(self) -> None:
        super().tearDown()

    def test_deploy(self):
        # gather arguments
        sys.argv = ["",
                    "deploy",
                    str(self.get_test_solution_path()),
                    "--dry-run=True",
                    "--trigger-pipeline=False",
                    "--git-name=MyName",
                    "--git-email=MyEmail",
                    ]

        self.assertIsNone(main())


if __name__ == '__main__':
    unittest.main()
