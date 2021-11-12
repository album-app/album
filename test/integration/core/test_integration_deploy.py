import sys
import unittest

from album.argument_parsing import main
from album.core.utils.operations.file_operations import force_remove
from album.runner.model.coordinates import Coordinates
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationDeploy(TestIntegrationCommon):

    def tearDown(self) -> None:
        # try to avoid git-removal windows errors
        try:
            force_remove(self.collection_manager.configuration.cache_path_download, warning=False)
        except TimeoutError:
            # todo: fixme! rather sooner than later!
            if sys.platform == 'win32' or sys.platform == 'cygwin':
                pass
        super().tearDown()

    def test_deploy_dry_run(self):
        catalog = self.add_test_catalog()
        # gather arguments
        sys.argv = ['',
                    'deploy',
                    str(self.get_test_solution_path()),
                    '--catalog=test_catalog',
                    '--dry-run',
                    '--git-name=MyName',
                    '--git-email=MyEmail',
                    ]

        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output)
        self.assertIn('Pretending to deploy', self.captured_output.getvalue())
        self.collection_manager.catalogs().update_any('test_catalog')
        updates = self.collection_manager.catalogs().update_collection('test_catalog')
        self.assertIn('test_catalog', updates)
        self.assertEqual(0, len(updates['test_catalog'].solution_changes))

    def test_deploy(self):
        catalog = self.add_test_catalog()
        # gather arguments
        sys.argv = ['',
                    'deploy',
                    str(self.get_test_solution_path()),
                    '--catalog',
                    'test_catalog',
                    '--changelog',
                    'something changed'
                    ]

        self.assertIsNone(main())
        self.assertNotIn("ERROR", self.captured_output)
        self.collection_manager.catalogs().update_any('test_catalog')
        updates = self.collection_manager.catalogs().update_collection('test_catalog')
        self.assertIn('test_catalog', updates)
        self.assertEqual(1, len(updates['test_catalog'].solution_changes))
        solution = self.collection_manager.catalog_collection.get_solution_by_catalog_grp_name_version(
            self.collection_manager.catalogs().get_by_name('test_catalog').catalog_id,
            Coordinates('group', 'name', '0.1.0')
        )
        self.assertIsNotNone(solution)
        self.assertIsNotNone(solution.setup['timestamp'])
        self.assertEqual('something changed', solution.setup['changelog'])


if __name__ == '__main__':
    unittest.main()
