import sys
from pathlib import Path
from shutil import copy

from album.core.model.default_values import DefaultValues
from album.runner.core.model.coordinates import Coordinates
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationDeploy(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    def test_deploy_dry_run(self):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)

        # call
        self.album_controller.deploy_manager().deploy(str(self.get_test_solution_path()), catalog_name=catalog.name(),
                                                      changelog='something changed', dry_run=True, git_name='MyName',
                                                      git_email='MyEmail')

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn('Pretending to deploy', self.captured_output.getvalue())
        self.album_controller.collection_manager().catalogs().update_any('test_catalog')
        updates = self.album_controller.collection_manager().catalogs().update_collection('test_catalog')
        self.assertIn('test_catalog', updates)
        self.assertEqual(0, len(updates['test_catalog'].solution_changes()))

    def test_deploy_file(self):
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)

        # call
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path()),
            catalog_name=catalog.name(),
            changelog='something changed',
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value
        )

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.album_controller.collection_manager().catalogs().update_any('test_catalog')
        updates = self.album_controller.collection_manager().catalogs().update_collection('test_catalog')
        self.assertIn('test_catalog', updates)
        self.assertEqual(1, len(updates['test_catalog'].solution_changes()))
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            self.album_controller.collection_manager().catalogs().get_by_name('test_catalog').catalog_id(),
            Coordinates('group', 'name', '0.1.0')
        )
        self.assertIsNotNone(solution)
        self.assertIsNotNone(solution.setup()['timestamp'])
        self.assertEqual('something changed', solution.setup()['changelog'])

    def test_deploy_folder_no_changelog(self):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)

        path = str(self.get_test_solution_path())
        coordinates = Coordinates('group', 'name', '0.1.0')

        # run deploy without changelog
        sys.argv = ['', 'deploy', path, '--catalog', 'test_catalog']

        # call
        self.album_controller.deploy_manager().deploy(
            path,
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value
        )

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertIn('We recommend documenting changes', self.captured_output.getvalue())

        # check if update exists, solution is present and has updated changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        updates = self.album_controller.collection_manager().catalogs().update_collection(catalog.name())
        self.assertIn(catalog.name(), updates)
        self.assertEqual(1, len(updates[catalog.name()].solution_changes()))
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates)
        self.assertIsNotNone(solution)
        self.assertEqual(None, solution.setup()['changelog'])

    def test_deploy_folder_changelog_parameter(self):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)

        path = str(self.get_test_solution_path())
        coordinates = Coordinates('group', 'name', '0.1.0')

        # call with changelog parameter
        self.album_controller.deploy_manager().deploy(
            path,
            catalog_name=catalog.name(),
            dry_run=False,
            changelog='something changed',
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value
        )

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertNotIn('We recommend documenting changes', self.captured_output.getvalue())

        # check if solution has provided changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        self.album_controller.collection_manager().catalogs().update_collection(catalog.name())
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates)
        self.assertIsNotNone(solution)
        self.assertIsNotNone(solution.setup()['timestamp'])
        self.assertEqual('something changed', solution.setup()['changelog'])

    def test_deploy_folder_changelog_file(self):
        # prepare
        path, _ = self.setup_empty_catalog("test_catalog")
        catalog = self.album_controller.collection_manager().catalogs().add_by_src(path)

        coordinates = Coordinates('group', 'name', '0.1.0')

        # copy solution and changelog file into new folder
        source = Path(self.tmp_dir.name).joinpath('mysolution')
        source.mkdir(parents=True)
        copy(self.get_test_solution_path("solution16_documentation.py"), source.joinpath('solution.py'))
        changelog_content = '# Changelog\nAll notable changes to this project will be documented in this file.\n\n' \
                            'The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), ' \
                            'and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).' \
                            '\n\n## [0.1.0] - %s\n%s\n\n' % ('21/11/25', '- my changes')

        with open(source.joinpath('CHANGELOG.md'), 'w') as file:
            file.write(changelog_content)
        with open(source.joinpath('file.md'), 'w') as file:
            file.write('my documentation')

        # call providing changelog via file
        self.album_controller.deploy_manager().deploy(
            str(source),
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value
        )

        # assert
        self.assertNotIn('ERROR', self.captured_output.getvalue())
        self.assertNotIn('We recommend documenting changes', self.captured_output.getvalue())

        # check if solution is present and has updated changelog
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        self.album_controller.collection_manager().catalogs().update_collection(catalog.name())
        solution = self.album_controller.collection_manager().catalog_collection.get_solution_by_catalog_grp_name_version(
            catalog.catalog_id(), coordinates)
        self.assertIsNotNone(solution)
        self.assertEqual('- my changes', str(solution.setup()['changelog'].strip()))

        # check if documentation file was deployed into the catalog and copied into the collection cache
        with catalog.retrieve_catalog(Path(self.tmp_dir.name).joinpath("tmp_cat_dir")) as tmp_repo:
            self.assertTrue(
                Path(tmp_repo.working_tree_dir).joinpath(
                    self.album_controller.configuration().get_solution_path_suffix(coordinates),
                    'file.md'
                ).exists()
            )
