import tempfile
import unittest.mock
from unittest.mock import patch
from pathlib import Path
from hips import HipsClass
from hips import api
from hips.hips_base import HipsDefaultValues
from test.unit.test_common import TestHipsCommon


def get_config_test_path():
    return Path(tempfile.gettempdir()).joinpath("ch")


def get_data_test_path():
    return Path(tempfile.gettempdir()).joinpath("data")


class TestHipsAPI(TestHipsCommon):

    def setUp(self):
        pass

    def test_get_base_cache_path(self):
        root = api.get_base_cache_path()
        self.assertIsNotNone(root)
        self.assertNotEqual("", root)

    @patch('hips.api.xdg_config_home')
    @patch('hips.api.xdg_data_home')
    def test_get_cache_path_hips(self, data_home_mock, config_home_mock):
        data_home_mock.side_effect = get_data_test_path
        config_home_mock.side_effect = get_config_test_path

        root = get_data_test_path().joinpath("hips")

        path = api.get_configuration_file_path()
        self.assertEqual(get_config_test_path().joinpath(HipsDefaultValues.hips_config_file_name.value), path)

        path = api.get_cache_path_hips(HipsClass({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("solutions/local/mygroup/myname/myversion"), path)

        path = api.get_cache_path_hips(HipsClass({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("solutions/doi/mydoi"), path)

        path = api.get_cache_path_downloads(HipsClass({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("downloads/local/mygroup/myname/myversion"), path)

        path = api.get_cache_path_downloads(HipsClass({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("downloads/doi/mydoi"), path)

        path = api.get_cache_path_catalog("mycatalog")
        self.assertEqual(root.joinpath("catalogs/mycatalog"), path)

        path = api.get_cache_path_app(HipsClass({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("apps", "local", "mygroup", "myname", "myversion"), path)

        path = api.get_cache_path_app(HipsClass({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("apps", "doi", "mydoi"), path)

    def test__extract_catalog_name(self):
        self.attrs = {
            "catalog": "https://gitlab.com/ida-mdc/hips-catalog.ext"
        }

        active_hips = HipsClass(self.attrs)

        self.assertEqual(api._extract_catalog_name(active_hips["catalog"]), "hips-catalog")

    @unittest.skip("Needs to be implemented!")
    def test_download_if_not_exists(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def extract_tar(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_download_hips_repository(self):
        # todo implement
        pass


if __name__ == '__main__':
    unittest.main()
