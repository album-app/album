import unittest
from pathlib import Path
from unittest.mock import patch

from hips.core.controller.conda_manager import CondaManager
from hips.core.utils.operations.file_operations import remove_warning_on_error
from test.unit.test_common import TestHipsCommon


class TestCondaManager(TestHipsCommon):
    test_environment_name = "unittest"

    def setUp(self):
        self.conda = CondaManager()

    def tearDown(self) -> None:
        env_dict = self.conda.get_environment_dict()
        if self.conda.environment_exists(self.test_environment_name):
            self.conda.remove_environment(self.test_environment_name)
            self.assertFalse(self.conda.environment_exists(self.test_environment_name))
            # try to delete rest of disc content
            remove_warning_on_error(env_dict[self.test_environment_name])
        CondaManager.instance = None
        super().tearDown()

    @patch('hips.core.controller.conda_manager.CondaManager.get_info')
    def test_get_environment_dict(self, ginfo_mock):
        ginfo_mock.return_value = {
            "envs": [Path("aPath").joinpath("envName1"), Path("anotherPath").joinpath("envName2")]
        }

        expected = dict()
        expected["envName1"] = Path("aPath").joinpath("envName1")
        expected["envName2"] = Path("anotherPath").joinpath("envName2")

        res = self.conda.get_environment_dict()

        self.assertEqual(expected, res)

    def test_get_base_environment_path(self):
        r = self.conda.get_base_environment_path()
        self.assertIsNotNone(r)
        self.assertTrue(Path(r).is_dir())

    @patch('hips.core.controller.conda_manager.CondaManager.get_environment_dict')
    def test_environment_exists(self, ged_mock):
        ged_mock.return_value = {
            "envName1": Path("aPath").joinpath("envName1"),
            "envName2": Path("anotherPath").joinpath("envName2")
        }

        self.assertTrue(self.conda.environment_exists("envName1"))
        self.assertFalse(self.conda.environment_exists("notExitendEnvs"))

    @patch('hips.core.controller.conda_manager.CondaManager.get_environment_dict')
    def test_get_environment_path(self, ged_mock):
        ged_mock.return_value = {
            "envName1": Path("aPath").joinpath("envName1"),
            "envName2": Path("anotherPath").joinpath("envName2")
        }
        self.assertEqual(Path("aPath").joinpath("envName1"), self.conda.get_environment_path("envName1"))

    @patch('hips.core.controller.conda_manager.CondaManager.get_info')
    def test_get_active_environment_name(self, ginfo_mock):
        ginfo_mock.return_value = {
            "active_prefix_name": "envName1"
        }
        self.assertEqual("envName1", self.conda.get_active_environment_name())

    @patch('hips.core.controller.conda_manager.CondaManager.get_info')
    def test_get_active_environment_path(self, ginfo_mock):
        ginfo_mock.return_value = {
            "active_prefix": "aEnvPath"
        }
        self.assertEqual("aEnvPath", self.conda.get_active_environment_path())

    def test_get_info(self):
        r = self.conda.get_info()

        self.assertIn("envs", r)
        self.assertIn("active_prefix_name", r)
        self.assertIn("active_prefix", r)

    def test_list_environment(self):
        p = self.conda.get_active_environment_path()
        r = self.conda.list_environment(p)

        self.assertIsNotNone(r)

    def test_is_installed(self):
        p = self.conda.get_active_environment_path()  # must have python installed - which it is if unit are running!
        self.assertTrue(self.conda.is_installed(p, "python"))
        self.assertFalse(self.conda.is_installed(p, "thisPackageDoesNotExist"))

    def test_create_environment_from_file_valid_file(self):
        self.assertFalse(self.conda.environment_exists(self.test_environment_name))
        env_file = """name: %s""" % self.test_environment_name

        with open(Path(self.tmp_dir.name).joinpath("env_file.yml"), "w") as f:
            f.writelines(env_file)

        self.conda.create_environment_from_file(
            Path(self.tmp_dir.name).joinpath("env_file.yml"), self.test_environment_name
        )

        self.assertTrue(self.conda.environment_exists(self.test_environment_name))

    def test_create_environment_from_file_invalid(self):
        # wrong file ending
        with self.assertRaises(NameError):
            self.conda.create_environment_from_file(self.closed_tmp_file.name, self.test_environment_name)

    def test_create_environment_from_file_valid_but_empty(self):
        t = Path(self.tmp_dir.name).joinpath("%s.yml" % self.test_environment_name)
        t.touch()
        # no content in file
        with self.assertRaises(ValueError):
            self.conda.create_environment_from_file(t, self.test_environment_name)

    def test_create_environment(self):
        self.assertFalse(self.conda.environment_exists(self.test_environment_name))

        skip = False

        try:
            self.conda.create_environment(self.test_environment_name)
        except RuntimeError as err:
            print(err)
            skip = True

        if not skip:
            # create it again without force fails
            with self.assertRaises(FileExistsError):
                self.conda.create_environment(self.test_environment_name)

            self.assertTrue(self.conda.environment_exists(self.test_environment_name))

            # check if python & pip installed
            self.assertTrue(
                self.conda.is_installed(self.conda.get_environment_path(self.test_environment_name), "python")
            )
            self.assertTrue(
                self.conda.is_installed(self.conda.get_environment_dict()[self.test_environment_name], "pip")
            )
        else:
            unittest.skip("WARNING - CONDA ERROR!")

    def test_pip_install(self):
        if not self.conda.environment_exists(self.test_environment_name):
            self.conda.create_environment(self.test_environment_name)

        p = self.conda.get_environment_dict()[self.test_environment_name]
        self.assertIsNotNone(p)

        # check if package NOT installed
        self.assertFalse(self.conda.is_installed(p, "anytree"))

        self.conda.pip_install(p, "anytree")

    def test_run_script(self):
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines("print(\"%s\")" % self.test_environment_name)

        p = self.conda.get_active_environment_path()

        self.conda.run_script(p, self.closed_tmp_file.name)

    @unittest.skip("Tested in tear_down() routine!")
    def test_remove_environment(self, active_env_mock):
        pass

    @patch('hips.core.utils.subcommand.run', return_value=True)
    def test_remove_environment_not_exist(self, run_mock):
        self.conda.create_environment(self.test_environment_name)
        run_mock.assert_called_once()

        # run_mock not called again
        self.conda.remove_environment("iDoNotExist")
        run_mock.assert_called_once()

    def test_cmd_available(self):
        if not self.conda.environment_exists(self.test_environment_name):
            self.conda.create_environment(self.test_environment_name)
        p = self.conda.get_environment_dict()[self.test_environment_name]

        self.assertFalse(self.conda.cmd_available(p, ["hips"]))
        self.assertTrue(self.conda.cmd_available(p, ["conda"]))

    def test_conda_install(self):
        if not self.conda.environment_exists(self.test_environment_name):
            self.conda.create_environment(self.test_environment_name)
        p = self.conda.get_environment_dict()[self.test_environment_name]

        self.assertFalse(self.conda.is_installed(p, "perl"))

        self.conda.conda_install(p, "perl")

        self.assertTrue(self.conda.is_installed(p, "perl"))


if __name__ == '__main__':
    unittest.main()
