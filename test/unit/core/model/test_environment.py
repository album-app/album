import io
import tempfile
import unittest.suite
from pathlib import Path
from unittest.mock import patch

from album.core.model.environment import Environment
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestEnvironment(TestUnitCoreCommon):
    test_environment_name = "unittest"

    def setUp(self):
        super().setUp()
        self.create_album_test_instance()

        """Setup things necessary for all tests of this class"""
        self.environment = Environment(None, self.test_environment_name, Path("aPath"))

    @patch('album.core.model.environment.Environment._prepare_env_file', return_value=None)
    def test_init_(self, prepare_env_file_mock):
        e = Environment(None, self.test_environment_name, Path("aPath"))

        prepare_env_file_mock.assert_called_once()

        self.assertIsNotNone(e)
        self.assertEqual(self.test_environment_name, e.name())
        self.assertEqual(Path("aPath"), e.cache_path())
        self.assertIsNone(e.yaml_file())

    def test__prepare_env_file_no_deps(self):
        self.assertIsNone(self.environment._prepare_env_file(None))

    def test__prepare_env_file_empty_deps(self):
        self.assertIsNone(self.environment._prepare_env_file({}))

    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test__prepare_env_file_invalid_file(self, create_path_mock):
        with self.assertRaises(TypeError) as context:
            self.environment._prepare_env_file({"environment_file": "env_file"})
            self.assertIn("Yaml file must either be a url", str(context.exception))

        create_path_mock.assert_called_once()

    @patch('album.core.model.environment.copy')
    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test__prepare_env_file_valid_file(self, create_path_mock, copy_mock):
        # mocks
        copy_mock.return_value = self.closed_tmp_file.name
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        r = self.environment._prepare_env_file({"environment_file": self.closed_tmp_file.name})

        self.assertEqual(self.closed_tmp_file.name, r)

        create_path_mock.assert_called_once()
        copy_mock.assert_called_once()

    @patch('album.core.model.environment.download_resource')
    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test__prepare_env_file_valid_url(self, create_path_mock, download_mock):
        # mocks
        download_mock.return_value = self.closed_tmp_file.name
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        url = "http://test.de"

        r = self.environment._prepare_env_file({"environment_file": url})

        self.assertEqual(self.closed_tmp_file.name, r)

        create_path_mock.assert_called_once()
        download_mock.assert_called_once_with(url, Path("aPath").joinpath("%s.yml" % self.test_environment_name))

    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test__prepare_env_file_invalid_StringIO(self, create_path_mock):
        self.environment._cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        with self.assertRaises(TypeError):
            self.environment._prepare_env_file({"environment_file": string_io})

        self.assertTrue(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name).exists())

        create_path_mock.assert_called_once()

    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test__prepare_env_file_valid_StringIO(self, create_path_mock):
        self.environment._cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""name: value""")

        r = self.environment._prepare_env_file({"environment_file": string_io})

        self.assertEqual(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name), r)

        with open(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name), "r") as f:
            lines = f.readlines()

        # overwritten name
        self.assertEqual(lines[0], "name: %s\n" % self.test_environment_name)

        create_path_mock.assert_called_once()


if __name__ == '__main__':
    unittest.main()
