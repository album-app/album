import sys
import unittest
from pathlib import Path
from shutil import copy

from album.argument_parsing import main
from album.core.utils.operations.file_operations import force_remove
from album.runner.model.coordinates import Coordinates
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationDeploy(TestIntegrationCommon):

    def tearDown(self) -> None:
        # try to avoid git-removal windows errors
        try:
            force_remove(self.album_instance.configuration().get_cache_path_download(), warning=False)
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
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn('Pretending to deploy', self.captured_output.getvalue())
        self.collection_manager.catalogs().update_any('test_catalog')
        updates = self.collection_manager.catalogs().update_collection('test_catalog')
        self.assertIn('test_catalog', updates)
        self.assertEqual(0, len(updates['test_catalog'].solution_changes))

    def test_deploy_file(self):
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
        self.assertNotIn('ERROR', self.captured_output.getvalue())
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

    def test_deploy_folder_no_changelog(self):

        # setup test
        catalog = self.add_test_catalog()
        path = str(self.get_test_solution_path())
        coordinates = Coordinates('group', 'name', '0.1.0')

        # run deploy without changelog
        sys.argv = ['', 'deploy', path, '--catalog', 'test_catalog']
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn('We recommend documenting changes', self.captured_output.getvalue())

        # check if update exists, solution is present and has updated changelog
        self.collection_manager.catalogs().update_any(catalog.name)
        updates = self.collection_manager.catalogs().update_collection(catalog.name)
        self.assertIn(catalog.name, updates)
        self.assertEqual(1, len(updates[catalog.name].solution_changes))
        solution = self.collection_manager.catalog_collection.get_solution_by_catalog_grp_name_version(catalog.catalog_id, coordinates)
        self.assertIsNotNone(solution)
        self.assertEqual(None, solution.setup['changelog'])

    def test_deploy_folder_changelog_parameter(self):

        # setup test
        catalog = self.add_test_catalog()
        path = str(self.get_test_solution_path())
        coordinates = Coordinates('group', 'name', '0.1.0')

        # run deploy with changelog parameter
        sys.argv = ['', 'deploy', path, '--catalog', catalog.name, '--changelog', 'something changed']
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertNotIn('We recommend documenting changes', self.captured_output.getvalue())

        # check if solution has provided changelog
        self.collection_manager.catalogs().update_any(catalog.name)
        self.collection_manager.catalogs().update_collection(catalog.name)
        solution = self.collection_manager.catalog_collection.get_solution_by_catalog_grp_name_version(catalog.catalog_id, coordinates)
        self.assertIsNotNone(solution)
        self.assertIsNotNone(solution.setup['timestamp'])
        self.assertEqual('something changed', solution.setup['changelog'])

    def test_deploy_folder_changelog_file(self):

        # setup test
        catalog = self.add_test_catalog()
        coordinates = Coordinates('group', 'name', '0.1.0')

        # copy solution and changelog file into new folder
        source = Path(self.tmp_dir.name).joinpath('mysolution')
        source.mkdir(parents=True)
        copy(self.get_test_solution_path(), source.joinpath('solution.py'))
        changelog_content = '# Changelog\nAll notable changes to this project will be documented in this file.\n\n' \
                            'The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), ' \
                            'and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).' \
                            '\n\n## [0.1.0] - %s\n%s\n\n' % ('21/11/25', '- my changes')
        with open(source.joinpath('CHANGELOG.md'), 'w') as file:
            file.write(changelog_content)
        with open(source.joinpath('file.md'), 'w') as file:
            file.write('my documentation')

        # run deploy while providing changelog via file
        sys.argv = ['', 'deploy', str(source), '--catalog', 'test_catalog']
        self.assertIsNone(main())
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertNotIn('We recommend documenting changes', self.captured_output.getvalue())

        # check if solution is present and has updated changelog
        self.collection_manager.catalogs().update_any(catalog.name)
        self.collection_manager.catalogs().update_collection(catalog.name)
        solution = self.collection_manager.catalog_collection.get_solution_by_catalog_grp_name_version(catalog.catalog_id, coordinates)
        self.assertIsNotNone(solution)
        self.assertEqual('- my changes', str(solution.setup['changelog'].strip()))

        # check of documentation file was deployed into the catalog and copied into the collection cache
        self.assertTrue(catalog.src.joinpath(self.album_instance.configuration().get_solution_path_suffix(coordinates), 'file.md').exists())


if __name__ == '__main__':
    unittest.main()
