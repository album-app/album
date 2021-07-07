import tempfile
import unittest
from pathlib import Path

from hips.core.model.configuration import HipsConfiguration, HipsDefaultValues
from test.unit.test_common import TestHipsCommon


class TestHipsConfiguration(TestHipsCommon):

    def setUp(self) -> None:
        HipsConfiguration.instance = None  # lever out concept
        self.conf = HipsConfiguration(
            base_cache_path=Path(self.tmp_dir.name).joinpath("hips"), configuration_file_path=self.tmp_dir.name
        )

    def tearDown(self) -> None:
        super().tearDown()

    def test_base_cache_path(self):
        new_tmp_dir = tempfile.TemporaryDirectory(dir=self.tmp_dir.name)

        # set
        self.conf.base_cache_path = new_tmp_dir.name

        # assert
        self.assertEqual(
            self.conf.base_cache_path,
            Path(new_tmp_dir.name)
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(HipsDefaultValues.cache_path_solution_prefix.value),
            self.conf.cache_path_solution
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(HipsDefaultValues.cache_path_app_prefix.value),
            self.conf.cache_path_app
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(HipsDefaultValues.cache_path_download_prefix.value),
            self.conf.cache_path_download
        )
        self.assertEqual(
            Path(new_tmp_dir.name).joinpath(HipsDefaultValues.cache_path_tmp_prefix.value),
            self.conf.cache_path_tmp
        )

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
