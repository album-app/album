import unittest
from pathlib import Path
from unittest.mock import patch

from hips.core.model.configuration import HipsConfiguration, HipsDefaultValues
from hips.core.model.hips_base import HipsClass
from test.unit.test_common import TestHipsCommon


class TestHipsConfiguration(TestHipsCommon):

    def setUp(self) -> None:
        HipsConfiguration.instance = None  # lever out concept
        self.conf = HipsConfiguration(
            base_cache_path=Path(self.tmp_dir.name).joinpath("hips"), configuration_file_path=self.tmp_dir.name
        )

    def tearDown(self) -> None:
        super().tearDown()

    @patch('hips.core.model.hips_base.HipsClass.get_hips_deploy_dict', return_value={})
    def test_get_cache_path_hips(self, _):
        root = Path(self.tmp_dir.name).joinpath("hips")

        path = self.conf.configuration_file_path.joinpath(".hips-config")
        self.assertEqual(Path(self.tmp_dir.name).joinpath(HipsDefaultValues.hips_config_file_name.value),
                         path)

        path = self.conf.get_cache_path_hips(
            HipsClass({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("solutions/local/mygroup/myname/myversion"), path)

        path = self.conf.get_cache_path_hips(HipsClass({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("solutions/doi/mydoi"), path)

        path = self.conf.get_cache_path_downloads(
            HipsClass({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("downloads/local/mygroup/myname/myversion"), path)

        path = self.conf.get_cache_path_downloads(HipsClass({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("downloads/doi/mydoi"), path)

        path = self.conf.get_cache_path_catalog("mycatalog")
        self.assertEqual(root.joinpath("catalogs/mycatalog"), path)

        path = self.conf.get_cache_path_app(
            HipsClass({"name": "myname", "group": "mygroup", "version": "myversion"}))
        self.assertEqual(root.joinpath("apps", "local", "mygroup", "myname", "myversion"), path)

        path = self.conf.get_cache_path_app(HipsClass({"doi": "mydoi"}))
        self.assertEqual(root.joinpath("apps", "doi", "mydoi"), path)

    def test_extract_catalog_name(self):
        catalog_name = "https://gitlab.com/ida-mdc/hips-catalog.ext"

        self.assertEqual(self.conf.extract_catalog_name(catalog_name), "hips-catalog")

    @unittest.skip("Needs to be implemented!")
    def test_get_default_hips_configuration(self):
        # ToDo: implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_get_default_catalog_configuration(self):
        # ToDo: implement
        pass


if __name__ == '__main__':
    unittest.main()
