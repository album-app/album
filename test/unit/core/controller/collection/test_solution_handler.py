import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.model.catalog import Catalog
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.file_operations import get_link_target
from album.core.utils.operations.resolve_operations import dict_to_coordinates
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.core.controller.collection.test_collection_manager import TestCatalogCollectionCommon


class TestSolutionHandler(TestCatalogCollectionCommon):

    def setUp(self):
        super().setUp()
        self.fill_catalog_collection()
        catalog_src = Path(self.tmp_dir.name).joinpath("testRepo")
        self.album.catalogs().create_new(catalog_src, "test")
        catalog_path = Path(self.tmp_dir.name).joinpath("testPath")
        catalog_path.mkdir(parents=True)

        self.catalog = Catalog(0, "test", src=catalog_src, path=catalog_path)
        self.solution_handler = self.collection_manager().solution_handler

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
        file = Path(self.solution_handler.get_solution_path(self.catalog, Coordinates("g", "n", "v"))).resolve()
        self.assertEqual(
            get_link_target(self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")).resolve(),
            file
        )

    def test_get_solution_file(self):
        # call
        file = Path(self.solution_handler.get_solution_file(self.catalog, Coordinates("g", "n", "v"))).resolve()
        res = get_link_target(self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")).joinpath("solution.py")
        self.assertEqual(res.resolve(), file)

    def test_get_solution_zip(self):
        # call
        solution_zip = Path(self.solution_handler.get_solution_zip(self.catalog, Coordinates("g", "n", "v"))).resolve()
        res = get_link_target(self.catalog.path().joinpath(DefaultValues.cache_path_solution_prefix.value, "g", "n", "v")).joinpath("g_n_v.zip")
        self.assertEqual(res.resolve(), solution_zip)

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


        # call & assert
        solution_path = self.solution_handler.retrieve_solution(self.catalog, Coordinates("g", "n", "v"))

        # assert
        dl_url = "http://NonsenseUrl" + "/-/raw/main/solutions/g/n/v/g_n_v.zip"
        dl_path = get_link_target(self.catalog.path().joinpath(
            DefaultValues.cache_path_solution_prefix.value, "g", "n", "v"
        )).joinpath("g_n_v.zip")
        res = Path("a/Path").joinpath(DefaultValues.solution_default_name.value)
        self.assertEqual(res, solution_path)

        dl_mock.assert_called_once_with(dl_url, dl_path)
        unzip_mock.assert_called_once_with(dl_path)

    def test_set_cache_paths(self):
        config = self.album.configuration()

        active_solution = Solution(self.solution_default_dict)
        path = self.album.configuration().get_cache_path_catalog("catalog_name_solution_lives_in")
        catalog = Catalog(0, "catalog_name_solution_lives_in", path)
        self.solution_handler.set_cache_paths(active_solution, catalog)

        self.assertEqual(
            Path(config.lnk_path()).joinpath('data', '0').resolve(),
            active_solution.installation().data_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('app', '0').resolve(),
            active_solution.installation().app_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('pck', '0').resolve(),
            active_solution.installation().package_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('icache', '0').resolve(),
            active_solution.installation().internal_cache_path().resolve()
        )
        self.assertEqual(
            Path(config.lnk_path()).joinpath('ucache', '0').resolve(),
            active_solution.installation().user_cache_path().resolve()
        )

    @patch('album.core.controller.collection.solution_handler.copy', return_value=None)
    def test_add_to_local_catalog(self, copy_mock):
        # run
        self.create_test_solution_no_env()
        self.active_solution.script = ""  # the script gets read during load()
        self.solution_handler.add_to_local_catalog(self.active_solution, "aPathToInstall")

        # assert
        path = self.solution_handler.get_solution_path(
            self.collection_manager().catalogs().get_local_catalog(),
            dict_to_coordinates(self.solution_default_dict))
        copy_mock.assert_called_once_with("aPathToInstall", path.joinpath('solution.py'))

    @unittest.skip("Needs to be implemented!")
    def test_write_version_to_yml(self):
        # todo: implement
        pass