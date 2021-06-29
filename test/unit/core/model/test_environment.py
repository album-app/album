import io
import json
import tempfile
import unittest.suite
from pathlib import Path
from unittest.mock import patch

from hips.core.model.environment import Environment
from test.unit.test_common import TestHipsCommon


class TestEnvironment(TestHipsCommon):
    test_environment_name = "unittest"

    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.environment = Environment(None, self.test_environment_name, "aPath")
        self.environment.name = self.test_environment_name

    @patch('hips.core.model.environment.Environment.get_env_file', return_value="Called")
    @patch('hips.core.model.environment.Environment.get_env_name', return_value="Called")
    def test_init_(self, get_env_file_mock, get_env_name_mock):
        e = Environment(None, self.test_environment_name, "aPath")

        get_env_file_mock.assert_called_once()
        get_env_name_mock.assert_called_once()

        self.assertIsNotNone(e)
        self.assertEqual(self.test_environment_name, e.cache_name)
        self.assertEqual(Path("aPath"), e.cache_path)

    @patch('hips.core.model.environment.Environment.create_or_update_env', return_value="Called")
    @patch('hips.core.model.environment.Environment.get_env_path', return_value="Called")
    @patch('hips.core.model.environment.Environment.install_hips', return_value="Called")
    def test_install(self, is_inst_mock, get_env_path_mock, create_mock):
        self.environment.install("TestVersion")

        create_mock.assert_called_once()
        get_env_path_mock.assert_called_once()
        is_inst_mock.assert_called_once_with("TestVersion")

    def test_get_env_file_no_deps(self):
        self.assertIsNone(self.environment.get_env_file(None))

    def test_get_env_file_empty_deps(self):
        self.assertIsNone(self.environment.get_env_file({}))

    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_invalid_file(self, create_path_mock):
        with self.assertRaises(RuntimeError) as context:
            self.environment.get_env_file({"environment_file": "env_file"})
            self.assertIn("No valid environment name", str(context.exception))

        create_path_mock.assert_called_once()

    @patch('hips.core.model.environment.copy', return_value="copiedPath")
    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_file(self, create_path_mock, copy_mock):
        with open(self.closed_tmp_file.name, mode="w") as tmp_file:
            tmp_file.write(self.test_environment_name)

        r = self.environment.get_env_file({"environment_file": self.closed_tmp_file.name})

        self.assertEqual(Path("aPath").joinpath("%s.yml" % self.test_environment_name), r)

        create_path_mock.assert_called_once()
        copy_mock.assert_called_once()

    @patch('hips.core.model.environment.download_resource', return_value="donwloadedResource")
    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_url(self, create_path_mock, download_mock):
        url = "http://test.de"

        r = self.environment.get_env_file({"environment_file": url})

        self.assertEqual("donwloadedResource", r)

        create_path_mock.assert_called_once()
        download_mock.assert_called_once_with(url, Path("aPath").joinpath("%s.yml" % self.test_environment_name))

    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_StringIO(self, create_path_mock):
        self.environment.cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        r = self.environment.get_env_file({"environment_file": string_io})

        self.assertEqual(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name), r)

        with open(Path(tempfile.gettempdir()).joinpath("%s.yml" % self.test_environment_name), "r") as f:
            lines = f.readlines()

        self.assertEqual(lines[0], "testStringIo")

        create_path_mock.assert_called_once()

    def test_get_env_name_no_deps(self):
        self.assertEqual(self.environment.get_env_name({}), 'hips')

    def test_get_env_name_invalid_deps(self):
        with self.assertRaises(RuntimeError):
            self.environment.get_env_name({"not_exist_file": "None"})

    def test_get_env_name_name_given(self):
        self.assertEqual(
            self.environment.get_env_name({"environment_name": self.test_environment_name}), self.test_environment_name
        )

    @patch('hips.core.model.environment.Environment.get_env_name_from_yaml', return_value="TheParsedName")
    def test_get_env_name_file_given(self, get_env_name_mock):
        self.assertEqual(
            self.environment.get_env_name({"environment_file": self.test_environment_name}), 'TheParsedName'
        )

        get_env_name_mock.assert_called_once()

    def test_get_env_name_from_yaml(self):
        with open(self.closed_tmp_file.name, "w") as tmp_file:
            tmp_file.write("name: TestName")

        self.environment.yaml_file = Path(self.closed_tmp_file.name)

        self.assertEqual(self.environment.get_env_name_from_yaml(), "TestName")

    @patch('hips.core.controller.conda_manager.CondaManager.get_environment_dict')
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

    @patch('hips.core.controller.conda_manager.CondaManager.get_environment_dict')
    def test_init_env_path(self, ged_mock):
        ged_mock.return_value = {
            self.test_environment_name: Path("aPath").joinpath(self.test_environment_name),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertIn("test", str(self.environment.init_env_path()))

    @patch('hips.core.controller.conda_manager.CondaManager.list_environment')
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

    @patch('hips.core.controller.conda_manager.CondaManager.run_script', return_value="ranScript")
    def test_run_script(self, conda_run_mock):
        script = "print(\"%s\")" % self.test_environment_name

        self.environment.path = "notNone"

        self.environment.run_scripts(script)
        conda_run_mock.assert_called_once()

    @patch('hips.core.controller.conda_manager.CondaManager.run_script', return_value="ranScript")
    def test_run_script_no_path(self, conda_run_mock):
        script = "print(\"%s\")" % self.test_environment_name

        self.environment.path = None

        with self.assertRaises(EnvironmentError):
            self.environment.run_scripts(script)
        conda_run_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.update')
    @patch('hips.core.model.environment.Environment.create')
    def test_create_or_update_env_no_env(self, create_mock, update_mock):
        self.environment.create_or_update_env()
        create_mock.assert_called_once()
        update_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.update')
    @patch('hips.core.model.environment.Environment.create')
    @patch('hips.core.controller.conda_manager.CondaManager.environment_exists')
    def test_create_or_update_env_env_present(self, ex_env_mock, create_mock, update_mock):
        ex_env_mock.return_value = True

        self.environment.create_or_update_env()
        update_mock.assert_called_once()
        create_mock.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_update(self):
        # ToDo: implement
        pass

    @patch('hips.core.controller.conda_manager.CondaManager.create_environment')
    @patch('hips.core.controller.conda_manager.CondaManager.create_environment_from_file')
    def test_create_valid_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.yaml_file = Path("aPath")

        self.environment.create()

        create_environment_from_file_mock.assert_called_once_with(Path("aPath"), self.test_environment_name)
        create_environment_mock.assert_not_called()

    @patch('hips.core.controller.conda_manager.CondaManager.create_environment')
    @patch('hips.core.controller.conda_manager.CondaManager.create_environment_from_file')
    def test_create_no_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.create()

        create_environment_mock.assert_called_once_with(self.test_environment_name)
        create_environment_from_file_mock.assert_not_called()

    @patch('hips.core.controller.conda_manager.CondaManager.cmd_available', return_value=True)
    @patch('hips.core.model.environment.Environment.pip_install')
    @patch('hips.core.model.environment.Environment.is_installed', return_value=False)
    def test_install_hips(self, is_installed_mock, pip_install_mock, cmd_available):
        self.environment.install_hips(None)

        cmd_available.assert_called_once()
        is_installed_mock.assert_called_once_with("hips-runner", None)
        pip_install_mock.assert_called_once_with('git+https://gitlab.com/ida-mdc/hips-runner.git')

    @patch('hips.core.controller.conda_manager.CondaManager.pip_install')
    def test_pip_install(self, conda_install_mock):
        self.environment.path = "aPath"
        self.environment.pip_install("test", "testVersion")

        conda_install_mock.assert_called_once_with("aPath", "test==testVersion")

    @patch('hips.core.controller.conda_manager.CondaManager.remove_environment')
    def test_remove(self, remove_mock):
        self.environment.remove()

        remove_mock.assert_called_once_with(self.test_environment_name)


if __name__ == '__main__':
    unittest.main()
