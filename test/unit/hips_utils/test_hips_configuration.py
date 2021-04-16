import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from hips_utils.hips_configuration import HipsConfiguration
from test.unit.test_common import TestHipsCommon


class TestConfiguration(TestHipsCommon):

    def setUp(self):
        self.tmp_dir = Path(tempfile.gettempdir())
        self.config_file = self.tmp_dir.joinpath("config_file")
        with open(self.config_file,  "w+") as f:
            f.write("""catalogs: [%s]""" % str(self.tmp_dir.joinpath("catalogs", "test_catalog")))

        self.config = HipsConfiguration(self.tmp_dir.joinpath("config_file"))

    def tearDown(self) -> None:
        try:
            Path(self.tmp_dir).joinpath("config_file").unlink()
        except FileNotFoundError:
            pass
        shutil.rmtree(Path(self.tmp_dir).joinpath("catalogs"), ignore_errors=True)

    def test__init__(self):
        self.assertTrue(self.config_file.is_file())
        self.assertEqual(len(self.config.catalogs), 1)
        with open(self.config_file, "r") as f:
            self.assertEqual(self.config.config_file_dict, yaml.safe_load(f))
        self.assertEqual(self.config.local_catalog, self.config.catalogs[0])

    def test_get_default_deployment_catalog(self):
        self.config.catalogs[0].is_local = False
        c = self.config.get_default_deployment_catalog()
        self.assertEqual(c.id, "test_catalog")

    def test_get_default_deployment_catalog_no_catalog(self):
        self.assertIsNone(self.config.get_default_deployment_catalog())

    def test_save(self):
        self.config.config_file_dict = {
            "catalogs": [str(self.tmp_dir.joinpath("catalogs", "test_catalog_save"))]
        }
        self.config.save()
        with open(self.config_file, "r") as f:
            self.assertEqual(
                yaml.safe_load(f),
                yaml.safe_load("{'catalogs': ['%s']}" % str(self.tmp_dir.joinpath("catalogs", "test_catalog_save")))
            )

    @patch('hips_utils.hips_configuration.get_dict_from_yml', return_value={""})
    def test__load_hips_configuration(self, get_dict_mock):
        config_file_dict = self.config._load_hips_configuration()

        get_dict_mock.assert_called_once()

        self.assertEqual(config_file_dict, {""})

    @patch('hips_utils.hips_configuration.get_dict_from_yml', return_value={})
    def test__load_hips_configuration_empty_file(self, get_dict_mock):

        with self.assertRaises(IOError):
            self.config._load_hips_configuration()

        get_dict_mock.assert_called_once()

    @patch('hips_utils.hips_configuration.HipsConfiguration._create_default_configuration', return_value="Called")
    @patch('hips_utils.hips_configuration.HipsConfiguration.save', return_value=None)
    def test__load_hips_configuration_no_file(self, save_mock, _create_default_mock):

        self.config.config_file_path = Path("doesNotExist")
        r = self.config._load_hips_configuration()

        _create_default_mock.assert_called_once()
        save_mock.assert_called_once_with("Called")

        self.assertEqual(r, "Called")

    @patch('hips_utils.hips_configuration.create_default_hips_configuration', return_value="Called")
    def test__create_default_configuration(self, create_default_mock):

        r = self.config._create_default_configuration()

        create_default_mock.assert_called_once()

        self.assertEqual(r, "Called")

    def test__get_catalogs_no_catalogs(self):
        self.config.config_file_dict = {}

        with self.assertRaises(RuntimeError):
            self.config._get_catalogs()

    def test__get_catalogs(self):
        c = self.config._get_catalogs()

        self.assertEqual(len(c), 1)

    def test__get_local_catalog_no_catalog(self):
        self.config.catalogs[0].is_local = False

        with self.assertRaises(RuntimeError):
            self.config._get_local_catalog()

    def test__get_local_catalog(self):
        r = self.config._get_local_catalog()

        self.assertEqual(r, self.config.catalogs[0])


if __name__ == '__main__':
    unittest.main()






