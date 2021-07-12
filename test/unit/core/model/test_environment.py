import io
import json
import tempfile
import unittest.suite
from pathlib import Path
from unittest.mock import patch

from album.core.model.environment import Environment
from test.unit.test_unit_common import TestUnitCommon


class TestEnvironment(TestUnitCommon):
    test_environment_name = "unittest"

    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.environment = Environment(None, self.test_environment_name, "aPath")

    @patch('album.core.model.environment.Environment.prepare_env_file', return_value=None)
    def test_init_(self, prepare_env_file_mock):
        e = Environment(None, self.test_environment_name, "aPath")

        prepare_env_file_mock.assert_called_once()

        self.assertIsNotNone(e)
        self.assertEqual(self.test_environment_name, e.name)
        self.assertEqual(Path("aPath"), e.cache_path)
        self.assertIsNone(e.yaml_file)

    @patch('album.core.model.environment.Environment.create_or_update_env', return_value="Called")
    @patch('album.core.model.environment.Environment.get_env_path', return_value="Called")
    @patch('album.core.model.environment.Environment.install_framework', return_value="Called")
    def test_install(self, is_inst_mock, get_env_path_mock, create_mock):
        self.environment.install("TestVersion")

        create_mock.assert_called_once()
        get_env_path_mock.assert_called_once()
        is_inst_mock.assert_called_once_with("TestVersion")

    def test_prepare_env_file_no_deps(self):
        self.assertIsNone(self.environment.prepare_env_file(None))

    def test_prepare_env_file_empty_deps(self):
        self.assertIsNone(self.environment.prepare_env_file({}))

    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_prepare_env_file_invalid_file(self, create_path_mock):
        with self.assertRaises(TypeError) as context:
            self.environment.prepare_env_file({"environment_file": "env_file"})
            self.assertIn("Yaml file must either be a url", str(context.exception))

        create_path_mock.assert_called_once()

    @patch('album.core.model.environment.copy')
    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_prepare_env_file_valid_file(self, create_path_mock, copy_mock):
        # mocks
        copy_mock.return_value = self.closed_tmp_file.name
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        r = self.environment.prepare_env_file({"environment_file": self.closed_tmp_file.name})

        self.assertEqual(self.closed_tmp_file.name, r)

        create_path_mock.assert_called_once()
        copy_mock.assert_called_once()

    @patch('album.core.model.environment.download_resource')
    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_url(self, create_path_mock, download_mock):
        # mocks
        download_mock.return_value = self.closed_tmp_file.name
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write("""name: test""")

        url = "http://test.de"

        r = self.environment.prepare_env_file({"environment_file": url})

        self.assertEqual(self.closed_tmp_file.name, r)

        create_path_mock.assert_called_once()
        download_mock.assert_called_once_with(url, Path("aPath").joinpath("%s.yml" % self.test_environment_name))

    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_invalid_StringIO(self, create_path_mock):
        self.environment.cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        with self.assertRaises(TypeError):
            self.environment.prepare_env_file({"environment_file": string_io})

        self.assertTrue(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name).exists())

        create_path_mock.assert_called_once()

    @patch('album.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_StringIO(self, create_path_mock):
        self.environment.cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""name: value""")

        r = self.environment.prepare_env_file({"environment_file": string_io})

        self.assertEqual(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name), r)

        with open(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name), "r") as f:
            lines = f.readlines()

        # overwritten name
        self.assertEqual(lines[0], "name: %s\n" % self.test_environment_name)

        create_path_mock.assert_called_once()

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_dict')
    def test_get_env_path(self, ged_mock):
        ged_mock.return_value = {
            self.test_environment_name: Path("aPath").joinpath(self.test_environment_name),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertIn(str(Path("aPath").joinpath(self.test_environment_name)), str(self.environment.get_env_path()))

    def test_get_env_path_invalid_env(self):
        self.assertFalse(self.environment.conda.environment_exists("NotExistingEnv"))
        self.environment.name = "NotExistingEnv"
        with self.assertRaises(RuntimeError):
            self.environment.get_env_path()

    def test_init_env_path_None(self):
        self.assertFalse(self.environment.conda.environment_exists("NotExistingEnv"))
        self.environment.name = "NotExistingEnv"

        self.assertIsNone(self.environment.init_env_path())

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_dict')
    def test_init_env_path(self, ged_mock):
        ged_mock.return_value = {
            self.test_environment_name: Path("aPath").joinpath(self.test_environment_name),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertIn("test", str(self.environment.init_env_path()))

    @patch('album.core.controller.conda_manager.CondaManager.list_environment')
    def test_is_installed(self, list_environment_mock):
        list_environment_mock.return_value = json.loads(
            """[
                {
                    "base_url": "https://repo.anaconda.com/pkgs/main",
                    "build_number": 3,
                    "build_string": "hdb3f193_3",
                    "channel": "pkgs/main",
                    "dist_name": "python-3.9.5-hdb3f193_3",
                    "name": "python",
                    "platform": "linux-64",
                    "version": "3.9.5"
                }
            ]"""
        )
        self.environment.path = "aPath"
        self.assertTrue(self.environment.is_installed("python"))
        self.assertTrue(self.environment.is_installed("python", "3.9.5"))
        self.assertFalse(self.environment.is_installed("python", "500.1"))
        self.assertTrue(self.environment.is_installed("python", "2.7"))

    @patch('album.core.controller.conda_manager.CondaManager.run_script', return_value="ranScript")
    def test_run_script(self, conda_run_mock):
        script = "print(\"%s\")" % self.test_environment_name

        self.environment.path = "notNone"

        self.environment.run_scripts(script)
        conda_run_mock.assert_called_once()

    @patch('album.core.controller.conda_manager.CondaManager.run_script', return_value="ranScript")
    def test_run_script_no_path(self, conda_run_mock):
        script = "print(\"%s\")" % self.test_environment_name

        self.environment.path = None

        with self.assertRaises(EnvironmentError):
            self.environment.run_scripts(script)
        conda_run_mock.assert_not_called()

    @patch('album.core.model.environment.Environment.update')
    @patch('album.core.model.environment.Environment.create')
    def test_create_or_update_env_no_env(self, create_mock, update_mock):
        self.environment.create_or_update_env()
        create_mock.assert_called_once()
        update_mock.assert_not_called()

    @patch('album.core.model.environment.Environment.update')
    @patch('album.core.model.environment.Environment.create')
    @patch('album.core.controller.conda_manager.CondaManager.environment_exists')
    def test_create_or_update_env_env_present(self, ex_env_mock, create_mock, update_mock):
        ex_env_mock.return_value = True

        self.environment.create_or_update_env()
        update_mock.assert_called_once()
        create_mock.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_update(self):
        # ToDo: implement
        pass

    @patch('album.core.controller.conda_manager.CondaManager.create_environment')
    @patch('album.core.controller.conda_manager.CondaManager.create_environment_from_file')
    def test_create_valid_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.yaml_file = Path("aPath")

        self.environment.create()

        create_environment_from_file_mock.assert_called_once_with(Path("aPath"), self.test_environment_name)
        create_environment_mock.assert_not_called()

    @patch('album.core.controller.conda_manager.CondaManager.create_environment')
    @patch('album.core.controller.conda_manager.CondaManager.create_environment_from_file')
    def test_create_no_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.create()

        create_environment_mock.assert_called_once_with(self.test_environment_name)
        create_environment_from_file_mock.assert_not_called()

    @patch('album.core.controller.conda_manager.CondaManager.cmd_available', return_value=True)
    @patch('album.core.model.environment.Environment.pip_install')
    @patch('album.core.model.environment.Environment.is_installed', return_value=False)
    def test_install_runner(self, is_installed_mock, pip_install_mock, cmd_available):
        self.environment.install_framework("version")

        cmd_available.assert_called_once()
        is_installed_mock.assert_called_once_with("album-runner", "version")
        pip_install_mock.assert_called_once_with('album-runner==version')

    @patch('album.core.controller.conda_manager.CondaManager.pip_install')
    def test_pip_install(self, conda_install_mock):
        self.environment.path = "aPath"
        self.environment.pip_install("test", "testVersion")

        conda_install_mock.assert_called_once_with("aPath", "test==testVersion")

    @patch('album.core.controller.conda_manager.CondaManager.remove_environment')
    def test_remove(self, remove_mock):
        self.environment.remove()

        remove_mock.assert_called_once_with(self.test_environment_name)


if __name__ == '__main__':
    unittest.main()
