import sys
import unittest

from album.argument_parsing import main
from album.core.utils.operations.file_operations import force_remove
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationDeploy(TestIntegrationCommon):

    def tearDown(self) -> None:
        # try to avoid git-removal windows errors
        try:
            force_remove(self.test_catalog_collection.configuration.cache_path_download, warning=False)
        except TimeoutError:
            # todo: fixme! rather sooner than later!
            if sys.platform == 'win32' or sys.platform == 'cygwin':
                pass
        super().tearDown()

    def test_deploy(self):
        # gather arguments
        sys.argv = ["",
                    "deploy",
                    str(self.get_test_solution_path()),
                    "--catalog=test_catalog",
                    "--dry-run=True",
                    "--trigger-pipeline=False",
                    "--git-name=MyName",
                    "--git-email=MyEmail",
                    ]

        self.assertIsNone(main())


if __name__ == '__main__':
    unittest.main()
