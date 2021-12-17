import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.core.controller.collection.test_collection_manager import TestCatalogCollectionCommon


class TestSolutionHandler(TestCatalogCollectionCommon):

    def setUp(self):
        super().setUp()
        self.fill_catalog_collection()
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        self.album.collection_manager().catalogs().create_new(catalog_src, "test")
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        self.catalog = Catalog(0, "test", src=catalog_src, path=catalog_path)
        self.solution_handler = self.collection_manager.solutions()

    def tearDown(self) -> None:
        super().tearDown()

    @unittest.skip("Needs to be implemented!")
    def test_add_or_replace(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_parent(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_solution(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_update_solution(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_apply_change(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_installed(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_uninstalled(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_installation_unfinished(self):
        # todo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_is_installed(self):
        # todo: implement
        pass

    def test_get_solution_path(self):
        # call
        self.assertEqual(
            self.solution_handler.get_solution_path(self.catalog, Coordinates("g", "n", "v")),
            self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")
        )

    def test_get_solution_file(self):
        res = self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v").joinpath("solution.py")

        # call
        self.assertEqual(res, self.solution_handler.get_solution_file(self.catalog, Coordinates("g", "n", "v")))

    def test_get_solution_zip(self):
        res = self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        # call
        self.assertEqual(res, self.solution_handler.get_solution_zip(self.catalog, Coordinates("g", "n", "v")))

    def test_get_solution_zip_suffix(self):
        res = Path("").joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip")

        # call
        self.assertEqual(res, self.solution_handler.get_solution_zip_suffix(Coordinates("g", "n", "v")))

    @patch("album.core.controller.collection.solution_handler.download_resource", return_value=None)
    @patch("album.core.controller.collection.solution_handler.unzip_archive", return_value=Path("a/Path"))
    def test_retrieve_solution(self, unzip_mock, dl_mock):
        # prepare
        self.catalog = Catalog(self.catalog.catalog_id(), self.catalog.name(), self.catalog.path(),
                               "http://NonsenseUrl.git")
        self.catalog.is_cache = MagicMock(return_value=False)

        dl_url = "http://NonsenseUrl" + "/-/raw/main/solutions/g/n/v/g_n_v.zip"
        dl_path = self.catalog.path().joinpath(
            DefaultValues.cache_path_solution_prefix.value, "g", "n", "v", "g_n_v.zip"
        )
        res = Path("a/Path").joinpath(DefaultValues.solution_default_name.value)

        # call & assert
        self.assertEqual(res, self.solution_handler.retrieve_solution(self.catalog, Coordinates("g", "n", "v")))

        # assert
        dl_mock.assert_called_once_with(dl_url, dl_path)
        unzip_mock.assert_called_once_with(dl_path)

    def test_set_cache_paths(self):
        config = self.album.configuration()

        active_solution = Solution(self.solution_default_dict)

        catalog = Catalog(0, "catalog_name_solution_lives_in", "")
        self.solution_handler.set_cache_paths(active_solution, catalog)

        self.assertEqual(
            Path(config.cache_path_download()).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation().data_path()
        )
        self.assertEqual(
            Path(config.cache_path_app()).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation().app_path()
        )
        self.assertEqual(
            catalog.path().joinpath(
                DefaultValues.cache_path_solution_prefix.value, "tsg", "tsn", "tsv"
            ),
            active_solution.installation().package_path()
        )
        self.assertEqual(
            Path(config.cache_path_tmp_internal()).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation().internal_cache_path()
        )
        self.assertEqual(
            Path(config.cache_path_tmp_user()).joinpath(
                "catalog_name_solution_lives_in", "tsg", "tsn", "tsv"
            ),
            active_solution.installation().user_cache_path()
        )
