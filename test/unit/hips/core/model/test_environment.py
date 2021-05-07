import io
import tempfile
import unittest.suite
from pathlib import Path
from unittest.mock import patch

from hips.core.model.environment import Environment, Conda
from test.unit.test_common import TestHipsCommon


class TestEnvironment(TestHipsCommon):

    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.environment = Environment({})
        self.environment.name = "test"

        pass

    @patch('hips.core.model.environment.Environment.get_env_file', return_value="Called")
    @patch('hips.core.model.environment.Environment.get_env_name', return_value="Called")
    def test_init_(self, get_env_file_mock, get_env_name_mock):
        e = Environment({"dependencies": None})

        get_env_file_mock.assert_called_once()
        get_env_name_mock.assert_called_once()

        self.assertIsNotNone(e.configuration)

    @patch('hips.core.model.environment.Environment.create_or_update_env', return_value="Called")
    @patch('hips.core.model.environment.Environment.get_env_path', return_value="Called")
    @patch('hips.core.model.environment.Environment.install_hips', return_value="Called")
    def test_install(self, is_inst_mock, get_env_path_mock, create_mock):
        self.environment.install("TestVersion")

        create_mock.assert_called_once()
        get_env_path_mock.assert_called_once()
        is_inst_mock.assert_called_once_with("TestVersion")

    def test_get_env_file_no_deps(self):
        self.assertIsNone(self.environment.get_env_file({}))

    def test_get_env_file_empty_deps(self):
        self.assertIsNone(self.environment.get_env_file({"dependencies": None}))

    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    @patch('hips.core.model.environment.HipsConfiguration.get_cache_path_hips', return_value=Path("aPath"))
    def test_get_env_file_invalid_file(self, _, create_path_mock):
        with self.assertRaises(RuntimeError) as context:
            self.environment.get_env_file({"name": "test", "dependencies": {"environment_file": "env_file"}})
            self.assertIn("No valid environment name", str(context.exception))

        create_path_mock.assert_called_once()

    @patch('hips.core.model.environment.copy', return_value="copiedPath")
    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    @patch('hips.core.model.environment.HipsConfiguration.get_cache_path_hips', return_value=Path("aPath"))
    def test_get_env_file_valid_file(self, _, create_path_mock, copy_mock):
        with tempfile.NamedTemporaryFile() as tmp_file:
            with open(tmp_file.name, "w") as f:
                f.write("test")

            r = self.environment.get_env_file({"name": "test", "dependencies": {"environment_file": tmp_file.name}})

            self.assertEqual(Path("aPath").joinpath("test.yml"), r)

            create_path_mock.assert_called_once()
            copy_mock.assert_called_once()

    @patch('hips.core.model.environment.download_resource', return_value="donwloadedResource")
    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    @patch('hips.core.model.environment.HipsConfiguration.get_cache_path_hips', return_value=Path("aPath"))
    def test_get_env_file_valid_url(self, _, create_path_mock, download_mock):
        url = "http://test.de"

        r = self.environment.get_env_file({"name": "test", "dependencies": {"environment_file": url}})

        self.assertEqual("donwloadedResource", r)

        create_path_mock.assert_called_once()
        download_mock.assert_called_once_with(url, Path("aPath").joinpath("test.yml"))

    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    @patch('hips.core.model.environment.HipsConfiguration.get_cache_path_hips')
    def test_get_env_file_valid_StringIO(self, get_path_mock, create_path_mock):
        get_path_mock.return_value = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        r = self.environment.get_env_file({"name": "test", "dependencies": {"environment_file": string_io}})

        self.assertEqual(Path(tempfile.gettempdir()).joinpath("test.yml"), r)

        with open(Path(tempfile.gettempdir()).joinpath("test.yml"), "r") as f:
            lines = f.readlines()

        self.assertEqual(lines[0], "testStringIo")

        create_path_mock.assert_called_once()

    def test_get_env_name_no_deps(self):
        self.assertEqual(self.environment.get_env_name({}), 'hips')

    def test_get_env_name_invalid_deps(self):
        with self.assertRaises(RuntimeError):
            self.assertEqual(self.environment.get_env_name({"dependencies": "None"}), 'hips')

    def test_get_env_name_name_given(self):
        self.assertEqual(self.environment.get_env_name({"dependencies": {"environment_name": "test"}}), 'test')

    @patch('hips.core.model.environment.Environment.get_env_name_from_yaml', return_value="TheParsedName")
    def test_get_env_name_file_given(self, get_env_name_mock):
        self.assertEqual(self.environment.get_env_name({"dependencies": {"environment_file": "test"}}), 'TheParsedName')

        get_env_name_mock.assert_called_once()

    def test_get_env_name_from_yaml(self):
        with tempfile.NamedTemporaryFile() as tmp_file:
            with open(tmp_file.name, "w") as f:
                f.write("name: TestName")

            self.environment.yaml_file = Path(tmp_file.name)

            self.assertEqual(self.environment.get_env_name_from_yaml(), "TestName")

    def test_get_env_path(self):
        Conda.create_environment("test")
        self.assertIn("test", self.environment.get_env_path())

    def test_get_env_path_invalid_env(self):
        self.assertFalse(Conda.environment_exists("NotExistingEnv"))
        self.environment.name = "NotExistingEnv"
        with self.assertRaises(RuntimeError):
            self.environment.get_env_path()

    def test_init_env_path_None(self):
        self.assertFalse(Conda.environment_exists("NotExistingEnv"))
        self.environment.name = "NotExistingEnv"

        self.assertIsNone(self.environment.init_env_path())

    def test_init_env_path(self):
        Conda.create_environment("test")

        self.assertIn("test", self.environment.init_env_path())

    def test_is_installed(self):
        Conda.create_environment("test")
        path = Conda.get_environment_dict()["test"]
        self.environment.path = path

        self.assertTrue(self.environment.is_installed("python"))
        self.assertFalse(self.environment.is_installed("python", "500.1"))
        self.assertTrue(self.environment.is_installed("python", "2.7"))

    @patch('hips.core.model.environment.Conda.run_script', return_value="ranScript")
    def test_run_script(self, conda_run_mock):
        script = "print(\"test\")"

        self.environment.path = "notNone"

        self.environment.run_script(script)
        conda_run_mock.assert_called_once()

    @patch('hips.core.model.environment.Conda.run_script', return_value="ranScript")
    def test_run_script_no_path(self, conda_run_mock):
        script = "print(\"test\")"

        self.environment.path = None

        with self.assertRaises(EnvironmentError):
            self.environment.run_script(script)
        conda_run_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.update')
    @patch('hips.core.model.environment.Environment.create')
    def test_create_or_update_env_no_env(self, create_mock, update_mock):
        Conda.remove_environment("test")
        self.assertFalse(Conda.environment_exists("test"))

        self.environment.create_or_update_env()
        create_mock.assert_called_once()
        update_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.update')
    @patch('hips.core.model.environment.Environment.create')
    def test_create_or_update_env_env_present(self, create_mock, update_mock):
        Conda.create_environment("test")

        self.environment.create_or_update_env()
        update_mock.assert_called_once()
        create_mock.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_update(self):
        # ToDo: implement
        pass

    @patch('hips.core.model.environment.Conda.create_environment')
    @patch('hips.core.model.environment.Conda.create_environment_from_file')
    def test_create_valid_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.yaml_file = Path("aPath")

        self.environment.create()

        create_environment_from_file_mock.assert_called_once_with(Path("aPath"), "test")
        create_environment_mock.assert_not_called()

    @patch('hips.core.model.environment.Conda.create_environment')
    @patch('hips.core.model.environment.Conda.create_environment_from_file')
    def test_create_no_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.create()

        create_environment_mock.assert_called_once_with("test")
        create_environment_from_file_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.pip_install')
    @patch('hips.core.model.environment.Environment.is_installed', return_value=False)
    def test_install_hips(self, is_installed_mock, pip_install_mock):
        self.environment.install_hips(None)

        is_installed_mock.assert_called_once_with("hips", None)
        pip_install_mock.assert_called_once_with('git+https://gitlab.com/ida-mdc/hips.git')

    @patch('hips.core.model.environment.Conda.pip_install')
    def test_pip_install(self, conda_install_mock):
        self.environment.path = "aPath"
        self.environment.pip_install("test", "testVersion")

        conda_install_mock.assert_called_once_with("aPath", "test==testVersion")

    @patch('hips.core.model.environment.Conda.remove_environment')
    def test_remove(self, remove_mock):
        self.environment.remove()

        remove_mock.assert_called_once_with("test")


if __name__ == '__main__':
    unittest.main()
