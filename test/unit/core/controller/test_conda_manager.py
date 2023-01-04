import json
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml

from album.core.controller.conda_manager import CondaManager
from album.core.controller.package_manager import PackageManager
from album.core.model.default_values import DefaultValues
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import _create_shortcut
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCondaManager(TestUnitCoreCommon):
    test_environment_name = "unittest"

    def setUp(self):
        super().setUp()
        self.setup_collection(init_catalogs=False, init_collection=True)
        self.conda = CondaManager(self.album_controller.configuration())

    def tearDown(self) -> None:
        if self.conda.environment_exists(self.test_environment_name):
            self.conda.remove_environment(self.test_environment_name)
            self.assertFalse(self.conda.environment_exists(self.test_environment_name))
        super().tearDown()

    def test_get_environment_list(self):
        base_dir = Path(self.album_controller.configuration().lnk_path()).joinpath(
            "env"
        )
        expected = list()
        expected.append(base_dir.joinpath("envName1").resolve())
        expected.append(base_dir.joinpath("envName2").resolve())
        Path(expected[0]).joinpath("somefile").mkdir(parents=True)
        Path(expected[1]).joinpath("somefile").mkdir(parents=True)

        res = self.conda.get_environment_list()

        self.assertListEqual(expected, res)
    @unittest.skipIf(platform.system() == "Windows", "This is a unittest which uses unix style links (symlinks)")
    @patch("album.core.controller.package_manager.PackageManager.get_environment_list")
    def test_environment_exists(self, ged_mock):
        p = str(self.conda._configuration.environments_path().joinpath("envName1"))
        target = self.conda._configuration.lnk_path().joinpath("0")
        Path(target).joinpath("whatever").mkdir(parents=True)
        os.symlink(target.resolve(), p)

        ged_mock.return_value = [target.resolve()]

        self.assertTrue(self.conda.environment_exists("envName1"))
        self.assertFalse(self.conda.environment_exists("notExitendEnvs"))

    @unittest.skipIf(platform.system() != "Windows", "This is a unittest which uses windows style links (.lnk)")
    @patch("album.core.controller.package_manager.PackageManager.get_environment_list")
    def test_environment_exists(self, ged_mock):
        p = str(self.conda._configuration.environments_path().joinpath("envName1"))
        target = self.conda._configuration.lnk_path().joinpath("0")
        Path(target).joinpath("whatever").mkdir(parents=True)
        _create_shortcut(p + ".lnk", target)

        ged_mock.return_value = [target.resolve()]

        self.assertTrue(self.conda.environment_exists("envName1"))
        self.assertFalse(self.conda.environment_exists("notExitendEnvs"))

    @patch("album.core.controller.package_manager.PackageManager.get_environment_list")
    def test_get_environment_path(self, ged_mock):
        link1 = self.conda._configuration.lnk_path().joinpath("env", "%s" % 0).resolve()
        ged_mock.return_value = [link1]
        self.assertEqual(link1, self.conda.get_environment_path("envName1").resolve())

    def test_get_environment_path_invalid_env(self):
        self.assertFalse(self.conda.environment_exists("NotExistingEnv"))
        name = "NotExistingEnv"
        with self.assertRaises(LookupError):
            self.conda.get_environment_path(name)

    @patch("album.core.controller.package_manager.PackageManager.get_info")
    def test_get_active_environment_name(self, ginfo_mock):
        ginfo_mock.return_value = {"active_prefix_name": "envName1"}
        self.assertEqual("envName1", self.conda.get_active_environment_name())

    @patch("album.core.controller.package_manager.PackageManager.get_info")
    def test_get_active_environment_path(self, ginfo_mock):
        ginfo_mock.return_value = {"active_prefix": "aEnvPath"}
        self.assertEqual("aEnvPath", str(self.conda.get_active_environment_path()))

    def test_get_info(self):
        r = self.conda.get_info()

        self.assertIn("envs", r)
        self.assertIn("active_prefix_name", r)
        self.assertIn("active_prefix", r)

    def test_list_environment(self):
        p = self.conda.get_active_environment_path()
        r = self.conda.list_environment(p)

        self.assertIsNotNone(r)

    def test_create_environment_from_file_valid_file(self):
        self.assertFalse(self.conda.environment_exists(self.test_environment_name))
        env_file = """dependencies:"""

        with open(Path(self.tmp_dir.name).joinpath("env_file.yml"), "w") as f:
            f.writelines(env_file)

        self.conda.create_environment_from_file(
            Path(self.tmp_dir.name).joinpath("env_file.yml"), self.test_environment_name
        )
        self.assertTrue(self.conda.environment_exists(self.test_environment_name))

    @unittest.skipIf(
        DefaultValues.runner_api_package_version.value is None,
        "Skipped because custom runner version is used",
    )
    def test__append_framework_to_yml_pip(self):
        output = PackageManager.append_framework_to_yml(
            yaml.safe_load(
                """
dependencies:
    - pip
    - pip:
         - bla
         - blub
"""
            ),
            "0.3.0",
        )
        self.assertEqual(
            {
                "dependencies": [
                    "conda-forge::album-solution-api=0.6.0",
                    "pip",
                    {"pip": ["bla", "blub"]},
                ]
            },
            output,
        )
        output = PackageManager.append_framework_to_yml(
            yaml.safe_load("""name: test"""), "0.3.0"
        )
        self.assertEqual(
            {
                "name": "test",
                "dependencies": ["conda-forge::album-solution-api=0.6.0"],
            },
            output,
        )

    @unittest.skipIf(
        DefaultValues.runner_api_package_version.value is None,
        "Skipped because custom runner version is used",
    )
    def test__append_framework_to_yml_conda(self):
        output = CondaManager.append_framework_to_yml(
            yaml.safe_load("""dependencies:\n  - python"""),
            "0.5.1",
        )
        self.assertEqual(
            {"dependencies": ["python", "conda-forge::album-solution-api=0.6.0"]},
            output,
        )

    def test_create_environment_from_file_invalid(self):
        # wrong file ending
        with self.assertRaises(NameError):
            self.conda.create_environment_from_file(
                self.closed_tmp_file.name, self.test_environment_name
            )

    def test_create_environment_from_file_valid_but_empty(self):
        t = Path(self.tmp_dir.name).joinpath("%s.yml" % self.test_environment_name)
        t.touch()
        # no content in file
        with self.assertRaises(ValueError):
            self.conda.create_environment_from_file(t, self.test_environment_name)

    def test_create_environment(self):
        self.assertFalse(self.conda.environment_exists(self.test_environment_name))

        skip = False  # The test checks if an environment error is raised when the same environment ist created two
        # times the skip variable is used two skip the second env creation call if the first one fails

        try:
            self.conda.create_environment(self.test_environment_name)
        except RuntimeError as err:
            print(err)
            skip = True

        if not skip:
            # create it again without force fails
            with self.assertRaises(EnvironmentError):
                self.conda.create_environment(self.test_environment_name)

            self.assertTrue(self.conda.environment_exists(self.test_environment_name))

            # check if python & pip installed
            self.assertTrue(
                self.conda.is_installed(
                    self.conda.get_environment_path(self.test_environment_name),
                    "python",
                )
            )
            self.assertTrue(
                self.conda.is_installed(
                    self.conda.get_environment_path(self.test_environment_name), "pip"
                )
            )
            # check if album-runner installed
            self.assertTrue(
                self.conda.is_installed(
                    self.conda.get_environment_path(self.test_environment_name),
                    "album-solution-api",
                )
            )
        else:
            unittest.skip("WARNING - CONDA ERROR!")

    @unittest.skip("Tested in tear_down() routine!")
    def test_remove_environment(self, active_env_mock):
        pass

    @patch("album.core.utils.subcommand.run", return_value=True)
    def test_remove_environment_not_exist(self, run_mock):
        self.conda.create_environment(self.test_environment_name)
        run_mock.assert_called_once()

        # run_mock not called again
        self.conda.remove_environment("iDoNotExist")
        run_mock.assert_called_once()

    def test_set_environment_path_None(self):
        name = "NotExistingEnv"
        self.assertFalse(self.conda.environment_exists(name))
        environment = Environment(None, name, "aPath")
        with self.assertRaises(LookupError):
            self.conda.set_environment_path(environment)

    @patch("album.core.controller.package_manager.PackageManager.get_environment_path")
    def test_set_environment_path(self, gep_mock):
        p = str(
            self.conda._configuration.environments_path().joinpath(
                self.test_environment_name
            )
        )
        gep_mock.return_value = p
        environment = Environment(None, self.test_environment_name, "aPath")
        self.assertIsNone(self.conda.set_environment_path(environment))

    @patch("album.core.controller.package_manager.PackageManager.list_environment")
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
        environment = Environment(None, "aName", "aPath")
        self.assertTrue(self.conda.is_installed(environment.path(), "python"))
        self.assertTrue(self.conda.is_installed(environment.path(), "python", "3.9.5"))
        self.assertFalse(self.conda.is_installed(environment.path(), "python", "500.1"))
        self.assertTrue(self.conda.is_installed(environment.path(), "python", "2.7"))

    @patch(
        "album.core.utils.subcommand.run",
        return_value="ranScript",
    )
    def test_run_script(self, run_mock):
        with tempfile.NamedTemporaryFile(mode="w") as tmp:
            tmp.write('print("%s")' % self.test_environment_name)
            environment = Environment(None, "aName", "aPath")
            environment._path = "NotNone"
            self.conda.run_script(environment, tmp.name)
            run_mock.assert_called_once()

    @patch(
        "album.core.utils.subcommand.run",
        return_value="ranScript",
    )
    def test_run_script_no_path(self, conda_run_mock):
        with tempfile.NamedTemporaryFile(mode="w") as tmp:
            tmp.write('print("%s")' % self.test_environment_name)
            environment = Environment(None, "aName", "aPath")
            environment._path = None

            with self.assertRaises(EnvironmentError):
                self.conda.run_script(environment, tmp.name)
            conda_run_mock.assert_not_called()

    def test_create_or_update_env_no_env(self):
        update_mock = MagicMock()
        create_mock = MagicMock()
        self.conda.update = update_mock
        self.conda.create = create_mock
        environment = Environment(None, "aName", "aPath")

        self.conda.create_or_update_env(environment)

        create_mock.assert_called_once_with(environment, None, None)
        update_mock.assert_not_called()

    @patch("album.core.controller.package_manager.PackageManager.create")
    @patch("album.core.controller.package_manager.PackageManager.update")
    @patch("album.core.controller.package_manager.PackageManager.environment_exists")
    def test_create_or_update_env_env_present(
        self, ex_env_mock, update_mock, create_mock
    ):

        ex_env_mock.return_value = True
        environment = Environment(None, "aName", "aPath")

        self.conda.create_or_update_env(environment)

        update_mock.assert_called_once_with(environment)
        create_mock.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_update(self):
        # ToDo: implement
        pass

    @patch("album.core.controller.package_manager.PackageManager.create_environment")
    @patch(
        "album.core.controller.package_manager.PackageManager.create_environment_from_file"
    )
    def test_create_valid_yaml(
        self, create_environment_from_file_mock, create_environment_mock
    ):
        environment = Environment(None, "aName", "aPath")
        environment._yaml_file = Path("aPath")

        self.conda.create(environment)

        create_environment_from_file_mock.assert_called_once_with(
            Path("aPath"), "aName", None
        )
        create_environment_mock.assert_not_called()

    @patch("album.core.controller.package_manager.PackageManager.create_environment")
    @patch(
        "album.core.controller.package_manager.PackageManager.create_environment_from_file"
    )
    def test_create_no_yaml(
        self, create_environment_from_file_mock, create_environment_mock
    ):
        environment = Environment(None, "aName", "aPath")
        self.conda.create(environment)

        create_environment_mock.assert_called_once_with("aName", None)
        create_environment_from_file_mock.assert_not_called()

    @patch(
        "album.core.controller.package_manager.PackageManager.create_or_update_env",
        return_value="Called",
    )
    @patch(
        "album.core.controller.package_manager.PackageManager.get_environment_path",
        return_value="Called",
    )
    def test_install(self, get_env_path_mock, create_mock):
        environment = Environment(None, "aName", "aPath")

        self.conda.install(environment, "TestVersion")

        create_mock.assert_called_once_with(environment, "TestVersion", None)
        get_env_path_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
