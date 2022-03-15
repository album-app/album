import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import force_remove
from album.core.utils.operations.git_operations import clone_repository
from album.core.utils.operations.solution_operations import serialize_json
from album.runner import album_logging
from album.runner.album_logging import LogLevel
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationAPI(TestIntegrationCoreCommon):

    def setUp(self):
        super().setUp()
        self.setup_album_instance()

    def tearDown(self) -> None:
        super().tearDown()

    def test_api(self):

        album_logging.set_loglevel(LogLevel.INFO)
        logger = album_logging.get_active_logger()

        album = self.album

        # list index
        catalogs_as_dict = album.get_index_as_dict()
        logger.info(serialize_json(catalogs_as_dict))

        # list catalogs without solutions
        catalogs_as_dict = album.get_catalogs_as_dict()
        logger.info(serialize_json(catalogs_as_dict))

        # list configuration
        logger.info(f"conda executable: {album.configuration().conda_executable()}")
        logger.info(f"album cache base: {album.configuration().base_cache_path()}")

        # add remote catalog
        remote_catalog = "https://gitlab.com/album-app/catalogs/templates/catalog"
        remote_catalog_instance = album.add_catalog(remote_catalog)

        # remove remote catalog
        album.remove_catalog_by_src(remote_catalog)

        # clone catalog template
        local_catalog_name = "mycatalog"
        local_catalogs_path = Path(self.tmp_dir.name).joinpath("my-catalogs")
        local_catalog_path = local_catalogs_path.joinpath(local_catalog_name)
        local_catalog_path_str = str(local_catalog_path)

        album.clone("template:catalog", local_catalog_path_str, local_catalog_name)

        self.assertCatalogPresence(self.album._controller.collection_manager().catalogs().get_all(), local_catalog_path,
                                   False)
        self.assertTrue(local_catalogs_path.exists())
        self.assertTrue(local_catalog_path.exists())
        # meta file available in catalog clone, not in catalog src, as it is a bare repository!
        with TemporaryDirectory(dir=self.album.configuration().cache_path_tmp_internal()) as tmp_dir:
            target_tmp = Path(tmp_dir).joinpath("clone")
            with clone_repository(local_catalog_path, target_tmp) as repo:
                self.assertTrue(
                    Path(repo.working_tree_dir).joinpath(DefaultValues.catalog_index_metafile_json.value).exists()
                )
            force_remove(target_tmp)

        # add catalog
        catalog = album.add_catalog(local_catalog_path)

        self.assertCatalogPresence(self.album._controller.collection_manager().catalogs().get_all(),
                                   str(local_catalog_path.resolve()), True)

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

        # assert that it's not installed
        album.clone(str(clone_src), str(solution_target_dir), solution_target_name)

        self.assertTrue(solution_target_dir.exists())
        self.assertTrue(solution_target_dir.joinpath(solution_target_name).exists())
        self.assertTrue(solution_target_file.exists())

        # deploy solution to catalog
        album.deploy(
            str(solution_target_file), local_catalog_name, dry_run=False, git_name="myname", git_email="mymail"
        )

        # update catalog cache
        album.update()

        # upgrade collection
        album.upgrade()

        solution_str = '%s:%s:%s' % (group, name, version)

        # check that solution exists, but is not installed
        installed = album.is_installed(solution_str)
        self.assertFalse(installed)

        # install solution
        album.install(solution_str)

        # check that solution is installed
        self.assertTrue(album.is_installed(solution_str))

        # run solution
        album.run(solution_str)

        # test solution
        album.test(solution_str)

        # uninstall solution
        album.uninstall(solution_str)

        # remove catalog
        album.remove_catalog_by_src(local_catalog_path)
        self.assertCatalogPresence(self.album._controller.collection_manager().catalogs().get_all(), local_catalog_path,
                                   False)

        # check that solution is not accessible any more
        # TODO

    def assertCatalogPresence(self, catalogs, src, should_be_present):
        present = False
        for catalog in catalogs:
            if str(catalog.src()) == src:
                present = True
        self.assertEqual(should_be_present, present)


if __name__ == '__main__':
    unittest.main()
