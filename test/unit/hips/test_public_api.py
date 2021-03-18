import unittest.mock
from unittest.mock import patch

from hips import Hips
from hips import public_api
from test.unit.test_common import TestHipsCommon


class TestHipsPublicAPI(TestHipsCommon):

    def setUp(self):
        pass

    def test_get_base_cache_path(self):
        root = public_api.get_base_cache_path()
        self.assertIsNotNone(root)
        self.assertNotEqual("", root)

    def test_get_cache_path_hips(self):
        root = public_api.get_base_cache_path()

        path = public_api.get_cache_path_hips(Hips({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("solutions/local/mygroup/myname/myversion"), path)

        path = public_api.get_cache_path_hips(Hips({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("solutions/doi/mydoi"), path)

        path = public_api.get_cache_path_downloads(Hips({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("downloads/local/mygroup/myname/myversion"), path)

        path = public_api.get_cache_path_downloads(Hips({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("downloads/doi/mydoi"), path)

        path = public_api.get_cache_path_catalog("mycatalog")
        self.assertEqual(root.joinpath("catalogs/mycatalog"), path)

    @patch('hips.public_api.get_cache_path_catalog', return_value="catalog")
    @patch('utils.git_operations.download_repository', return_value=True)
    def test_download_hips_catalog(self, dl_mock, getCache_mock):
        self.attrs = {
            "catalog": "https://gitlab.com/ida-mdc/hips-catalog.ext"
        }

        active_hips = Hips(self.attrs)

        public_api.download_hips_catalog(active_hips)

        dl_mock.assert_called_once_with("https://gitlab.com/ida-mdc/hips-catalog.ext", "catalog")
        getCache_mock.assert_called_once()

    def test__extract_catalog_name(self):
        self.attrs = {
            "catalog": "https://gitlab.com/ida-mdc/hips-catalog.ext"
        }

        active_hips = Hips(self.attrs)

        self.assertEqual(public_api._extract_catalog_name(active_hips["catalog"]), "hips-catalog")

    @unittest.skip("Needs to be implemented!")
    def test_download_if_not_exists(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def extract_tar(self):
        # TODO implement
        pass


if __name__ == '__main__':
    unittest.main()
