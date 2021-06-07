import unittest
from pathlib import Path
from unittest.mock import patch

from hips.core.utils.conda import Conda
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
        p = Conda.get_active_environment_path()  # must have python installed - which it is if unit are running!
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

        # check if package NOT installed
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

        self.assertFalse(Conda.cmd_available(p, ["hips"]))
        self.assertTrue(Conda.cmd_available(p, ["conda"]))

    def test_conda_install(self):
        Conda.create_environment("unit-test")
        p = Conda.get_environment_dict()["unit-test"]

        self.assertFalse(Conda.is_installed(p, "perl"))

        Conda.conda_install(p, "perl")

        self.assertTrue(Conda.is_installed(p, "perl"))