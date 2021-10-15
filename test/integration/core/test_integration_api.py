import json
import unittest
from pathlib import Path

from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.runner import logging
from album.runner.logging import LogLevel
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationAPI(TestIntegrationCommon):

    def test_api(self):

        logging.set_loglevel(LogLevel.INFO)
        logger = logging.get_active_logger()

        album = self.get_album()

        # list index
        catalogs_as_dict = album.collection_manager().get_index_as_dict()
        logger.info(json.dumps(catalogs_as_dict, sort_keys=True, indent=4))

        # list catalogs without solutions
        catalogs_as_dict = album.collection_manager().catalogs().get_all_as_dict()
        logger.info(json.dumps(catalogs_as_dict, sort_keys=True, indent=4))

        # list configuration
        logger.info(f"conda executable: {album.configuration().conda_executable}")
        logger.info(f"album cache base: {album.configuration().base_cache_path}")

        # add remote catalog
        remote_catalog = "https://gitlab.com/album-app/catalogs/templates/catalog"
        album.collection_manager().catalogs().add_by_src(remote_catalog)

        # remove remote catalog
        album.collection_manager().catalogs().remove_from_collection_by_src(remote_catalog)

        # clone catalog template
        local_catalog_name = "mycatalog"
        local_catalogs_path = Path(self.tmp_dir.name).joinpath("my-catalogs")
        local_catalogs = str(local_catalogs_path)
        local_catalog_path = local_catalogs_path.joinpath(local_catalog_name)

        album.clone_manager().clone("template:catalog", local_catalogs, local_catalog_name)

        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), local_catalog_path, False)
        self.assertTrue(local_catalogs_path.exists())
        self.assertTrue(local_catalog_path.exists())
        self.assertTrue(local_catalog_path.joinpath(DefaultValues.catalog_index_metafile_json.value).exists())

        # add catalog
        catalog = album.collection_manager().catalogs().add_by_src(local_catalog_path)

        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), str(local_catalog_path), True)

        # clone solution

        group = "group"
        name = "solution7_long_routines"
        version = "0.1.0"
        clone_src = self.get_test_solution_path(f"{name}.py")
        solution_target_dir = Path(self.tmp_dir.name).joinpath("my-solutions")
        solution_target_name = "my-" + name
        solution_target_file = solution_target_dir.joinpath(
            solution_target_name,
            DefaultValues.solution_default_name.value
        )
        solution_coordinates = Coordinates(group, name, version)

        # assert that it's not installed
        album.clone_manager().clone(str(clone_src), str(solution_target_dir), solution_target_name)

        self.assertTrue(solution_target_dir.exists())
        self.assertTrue(solution_target_dir.joinpath(solution_target_name).exists())
        self.assertTrue(solution_target_file.exists())

        # deploy solution to catalog
        album.deploy_manager().deploy(solution_target_file, local_catalog_name, dry_run=False)

        # update catalog cache
        album.collection_manager().catalogs().update_any(local_catalog_name)

        # upgrade collection
        album.collection_manager().catalogs().update_collection(local_catalog_name)

        # check that solution exists, but is not installed
        installed = album.collection_manager().solutions().is_installed(catalog, solution_coordinates)
        self.assertFalse(installed)

        # install solution
        album.install_manager().install_from_catalog_coordinates(local_catalog_name, solution_coordinates)

        # check that solution is installed
        self.assertTrue(album.collection_manager().solutions().is_installed(catalog, solution_coordinates))

        # run solution
        album.run_manager().run_from_catalog_coordinates(local_catalog_name, solution_coordinates)

        # test solution
        album.test_manager().test_from_catalog_coordinates(local_catalog_name, solution_coordinates)

        # remove catalog
        album.collection_manager().catalogs().remove_from_collection_by_src(local_catalog_path)
        self.assertCatalogPresence(self.collection_manager.catalogs().get_all(), local_catalog_path, False)

        # check that solution is not accessible any more
        # TODO

    def assertCatalogPresence(self, catalogs, src, should_be_present):
        present = False
        for catalog in catalogs:
            if str(catalog.src) == src:
                present = True
        self.assertEqual(should_be_present, present)


if __name__ == '__main__':
    unittest.main()
