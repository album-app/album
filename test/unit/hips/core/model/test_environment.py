import io
import json
import tempfile
import unittest.suite
from pathlib import Path
from unittest.mock import patch

from hips.core.model.environment import Environment, Conda
from test.unit.test_common import TestHipsCommon


class TestConda(TestHipsCommon):

    def setUp(self):
        pass

    def tearDown(self) -> None:
        if Conda.environment_exists("unit-test"):
            Conda.remove_environment("unit-test")
            self.assertFalse(Conda.environment_exists("unit-test"))
        super().tearDown()

    @patch('hips.core.model.environment.Conda.get_info')
    def test_get_environment_dict(self, ginfo_mock):
        ginfo_mock.return_value = {
            "envs": [Path("aPath").joinpath("envName1"), Path("anotherPath").joinpath("envName2")]
        }

        expected = dict()
        expected["envName1"] = Path("aPath").joinpath("envName1")
        expected["envName2"] = Path("anotherPath").joinpath("envName2")

        res = Conda.get_environment_dict()

        self.assertEqual(expected, res)

    def test_get_base_environment_path(self):
        r = Conda.get_base_environment_path()
        self.assertIsNotNone(r)
        self.assertTrue(Path(r).is_dir())

    @patch('hips.core.model.environment.Conda.get_environment_dict')
    def test_environment_exists(self, ged_mock):
        ged_mock.return_value = {
            "envName1": Path("aPath").joinpath("envName1"),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertTrue(Conda.environment_exists("envName1"))
        self.assertFalse(Conda.environment_exists("notExitendEnvs"))

    @patch('hips.core.model.environment.Conda.get_info')
    def test_get_active_environment_name(self, ginfo_mock):
        ginfo_mock.return_value = {
            "active_prefix_name": "envName1"
        }
        self.assertEqual("envName1", Conda.get_active_environment_name())

    @patch('hips.core.model.environment.Conda.get_info')
    def test_get_active_environment_path(self, ginfo_mock):
        ginfo_mock.return_value = {
            "active_prefix": "aEnvPath"
        }
        self.assertEqual("aEnvPath", Conda.get_active_environment_path())

    def test_get_info(self):
        r = Conda.get_info()

        self.assertIn("envs", r)
        self.assertIn("active_prefix_name", r)
        self.assertIn("active_prefix", r)

    def test_list_environment(self):
        p = Conda.get_active_environment_path()
        r = Conda.list_environment(p)

        self.assertIsNotNone(r)

    def test_is_installed(self):
        p = Conda.get_active_environment_path()  # must have python installed - which it is if unittest are running!
        self.assertTrue(Conda.is_installed(p, "python"))
        self.assertFalse(Conda.is_installed(p, "thisPackageDoesNotExist"))

    def test_create_environment_from_file_valid_file(self):
        self.assertFalse(Conda.environment_exists("unit-test"))
        env_file = """name: unit-test"""

        with open(Path(self.tmp_dir.name).joinpath("env_file.yml"), "w") as f:
            f.writelines(env_file)

        Conda.create_environment_from_file(Path(self.tmp_dir.name).joinpath("env_file.yml"), "unit-test")

        self.assertTrue(Conda.environment_exists("unit-test"))

    def test_create_environment_from_file_invalid(self):
        # wrong file ending
        with self.assertRaises(NameError):
            Conda.create_environment_from_file(self.closed_tmp_file.name, "unit-test")

    def test_create_environment_from_file_valid_but_empty(self):
        t = Path(self.tmp_dir.name).joinpath("unit-test.yml")
        t.touch()
        # no content in file
        with self.assertRaises(ValueError):
            Conda.create_environment_from_file(t, "unit-test")

    def test_create_environment(self):
        self.assertFalse(Conda.environment_exists("unit-test"))
        Conda.create_environment("unit-test")
        self.assertTrue(Conda.environment_exists("unit-test"))

        # check if python & pip installed
        self.assertTrue(Conda.is_installed(Conda.get_environment_dict()["unit-test"], "python"))
        self.assertTrue(Conda.is_installed(Conda.get_environment_dict()["unit-test"], "pip"))

    def test_pip_install(self):
        self.assertFalse(Conda.environment_exists("unit-test"))

        Conda.create_environment("unit-test")

        p = Conda.get_environment_dict()["unit-test"]
        self.assertIsNotNone(p)

        # check if python NOT installed
        self.assertFalse(Conda.is_installed(p, "anytree"))

        Conda.pip_install(p, "anytree")

    def test_run_script(self):
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines("print(\"unit-test\")")

        p = Conda.get_active_environment_path()

        Conda.run_script(p, self.closed_tmp_file.name)

    @unittest.skip("Tested in tear_down() routine!")
    def test_remove_environment(self, active_env_mock):
        pass

    @patch('hips.core.utils.subcommand.run', return_value=True)
    def test_remove_environment_not_exist(self, run_mock):
        Conda.create_environment("unit-test")
        run_mock.assert_called_once()

        # run_mock not called again
        Conda.remove_environment("iDoNotExist")
        run_mock.assert_called_once()

    def test_cmd_available(self):
        Conda.create_environment("unit-test")
        p = Conda.get_environment_dict()["unit-test"]

        self.assertFalse(Conda.cmd_available(p, "hips"))
        self.assertTrue(Conda.cmd_available(p, "conda"))

    def test_conda_install(self):
        Conda.create_environment("unit-test")
        p = Conda.get_environment_dict()["unit-test"]

        self.assertFalse(Conda.is_installed(p, "perl"))

        Conda.conda_install(p, "perl")

        self.assertTrue(Conda.is_installed(p, "perl"))


class TestEnvironment(TestHipsCommon):

    def setUp(self):
        """Setup things necessary for all tests of this class"""
        self.environment = Environment(None, "unit-test", "aPath")
        self.environment.name = "unit-test"

    @patch('hips.core.model.environment.Environment.get_env_file', return_value="Called")
    @patch('hips.core.model.environment.Environment.get_env_name', return_value="Called")
    def test_init_(self, get_env_file_mock, get_env_name_mock):
        e = Environment(None, "unit-test", "aPath")

        get_env_file_mock.assert_called_once()
        get_env_name_mock.assert_called_once()

        self.assertIsNotNone(e)
        self.assertEqual("unit-test", e.cache_name)
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
            tmp_file.write("unit-test")

        r = self.environment.get_env_file({"environment_file": self.closed_tmp_file.name})

        self.assertEqual(Path("aPath").joinpath("unit-test.yml"), r)

        create_path_mock.assert_called_once()
        copy_mock.assert_called_once()

    @patch('hips.core.model.environment.download_resource', return_value="donwloadedResource")
    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_url(self, create_path_mock, download_mock):
        url = "http://test.de"

        r = self.environment.get_env_file({"environment_file": url})

        self.assertEqual("donwloadedResource", r)

        create_path_mock.assert_called_once()
        download_mock.assert_called_once_with(url, Path("aPath").joinpath("unit-test.yml"))

    @patch('hips.core.model.environment.create_path_recursively', return_value="createdPath")
    def test_get_env_file_valid_StringIO(self, create_path_mock):
        self.environment.cache_path = Path(tempfile.gettempdir())

        string_io = io.StringIO("""testStringIo""")

        r = self.environment.get_env_file({"environment_file": string_io})

        self.assertEqual(Path(tempfile.gettempdir()).joinpath("unit-test.yml"), r)

        with open(Path(tempfile.gettempdir()).joinpath("unit-test.yml"), "r") as f:
            lines = f.readlines()

        self.assertEqual(lines[0], "testStringIo")

        create_path_mock.assert_called_once()

    def test_get_env_name_no_deps(self):
        self.assertEqual(self.environment.get_env_name({}), 'hips')

    def test_get_env_name_invalid_deps(self):
        with self.assertRaises(RuntimeError):
            self.environment.get_env_name({"not_exist_file": "None"})

    def test_get_env_name_name_given(self):
        self.assertEqual(self.environment.get_env_name({"environment_name": "unit-test"}), 'unit-test')

    @patch('hips.core.model.environment.Environment.get_env_name_from_yaml', return_value="TheParsedName")
    def test_get_env_name_file_given(self, get_env_name_mock):
        self.assertEqual(self.environment.get_env_name({"environment_file": "unit-test"}), 'TheParsedName')

        get_env_name_mock.assert_called_once()

    def test_get_env_name_from_yaml(self):
        with open(self.closed_tmp_file.name, "w") as tmp_file:
            tmp_file.write("name: TestName")

        self.environment.yaml_file = Path(self.closed_tmp_file.name)

        self.assertEqual(self.environment.get_env_name_from_yaml(), "TestName")

    @patch('hips.core.model.environment.Conda.get_environment_dict')
    def test_get_env_path(self, ged_mock):
        ged_mock.return_value = {
            "unit-test": Path("aPath").joinpath("unit-test"),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertIn(str(Path("aPath").joinpath("unit-test")), str(self.environment.get_env_path()))

    def test_get_env_path_invalid_env(self):
        self.assertFalse(Conda.environment_exists("NotExistingEnv"))
        self.environment.name = "NotExistingEnv"
        with self.assertRaises(RuntimeError):
            self.environment.get_env_path()

    def test_init_env_path_None(self):
        self.assertFalse(Conda.environment_exists("NotExistingEnv"))
        self.environment.name = "NotExistingEnv"

        self.assertIsNone(self.environment.init_env_path())

    @patch('hips.core.model.environment.Conda.get_environment_dict')
    def test_init_env_path(self, ged_mock):
        ged_mock.return_value = {
            "unit-test": Path("aPath").joinpath("unit-test"),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertIn("test", str(self.environment.init_env_path()))

    @patch('hips.core.model.environment.Conda.list_environment')
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

    @patch('hips.core.model.environment.Conda.run_script', return_value="ranScript")
    def test_run_script(self, conda_run_mock):
        script = "print(\"unit-test\")"

        self.environment.path = "notNone"

        self.environment.run_script(script)
        conda_run_mock.assert_called_once()

    @patch('hips.core.model.environment.Conda.run_script', return_value="ranScript")
    def test_run_script_no_path(self, conda_run_mock):
        script = "print(\"unit-test\")"

        self.environment.path = None

        with self.assertRaises(EnvironmentError):
            self.environment.run_script(script)
        conda_run_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.update')
    @patch('hips.core.model.environment.Environment.create')
    def test_create_or_update_env_no_env(self, create_mock, update_mock):
        self.environment.create_or_update_env()
        create_mock.assert_called_once()
        update_mock.assert_not_called()

    @patch('hips.core.model.environment.Environment.update')
    @patch('hips.core.model.environment.Environment.create')
    @patch('hips.core.model.environment.Conda.environment_exists')
    def test_create_or_update_env_env_present(self, ex_env_mock, create_mock, update_mock):
        ex_env_mock.return_value = True

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

        create_environment_from_file_mock.assert_called_once_with(Path("aPath"), "unit-test")
        create_environment_mock.assert_not_called()

    @patch('hips.core.model.environment.Conda.create_environment')
    @patch('hips.core.model.environment.Conda.create_environment_from_file')
    def test_create_no_yaml(self, create_environment_from_file_mock, create_environment_mock):
        self.environment.create()

        create_environment_mock.assert_called_once_with("unit-test")
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

        remove_mock.assert_called_once_with("unit-test")


if __name__ == '__main__':
    unittest.main()
