import json
import os
import platform
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.controller.conda_manager import CondaManager
from album.core.model.environment import Environment
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestCondaManager(TestUnitCoreCommon):
    test_environment_name = "unittest"

    def setUp(self):
        super().setUp()
        album = self.create_album_test_instance(init_catalogs=False)
        self.conda = CondaManager(album.configuration())

    def tearDown(self) -> None:
        if self.conda.environment_exists(self.test_environment_name):
            self.conda.remove_environment(self.test_environment_name)
            self.assertFalse(self.conda.environment_exists(self.test_environment_name))
        super().tearDown()

    def test_get_environment_list(self):
        base_dir = Path(self.album.configuration().lnk_path()).joinpath('env')
        expected = list()
        expected.append(base_dir.joinpath("envName1").resolve())
        expected.append(base_dir.joinpath("envName2").resolve())
        Path(expected[0]).joinpath('somefile').mkdir(parents=True)
        Path(expected[1]).joinpath('somefile').mkdir(parents=True)

        res = self.conda.get_environment_list()

        self.assertListEqual(expected, res)

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_list')
    def test_environment_exists(self, ged_mock):
        p = str(self.conda._configuration.cache_path_envs().joinpath("envName1"))
        target = self.conda._configuration.lnk_path().joinpath('0').resolve()
        Path(target).joinpath('whatever').mkdir(parents=True)
        operation_system = platform.system().lower()
        if 'windows' in operation_system:
            from pylnk3 import for_file
            for_file(
                target_file=str(target),
                lnk_name=p+'.lnk'
            )
        else:
            os.symlink(target, p)

        ged_mock.return_value = [target]

        self.assertTrue(self.conda.environment_exists("envName1"))
        self.assertFalse(self.conda.environment_exists("notExitendEnvs"))

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_list')
    def test_get_environment_path(self, ged_mock):
        link1 = self.conda._configuration.lnk_path().joinpath('env', '%s' % 0).resolve()
        ged_mock.return_value = [
            link1
        ]
        self.assertEqual(link1, self.conda.get_environment_path("envName1").resolve())

    def test_get_environment_path_invalid_env(self):
        self.assertFalse(self.conda.environment_exists("NotExistingEnv"))
        name = "NotExistingEnv"
        with self.assertRaises(LookupError):
            self.conda.get_environment_path(name)

    @patch('album.core.controller.conda_manager.CondaManager.get_info')
    def test_get_active_environment_name(self, ginfo_mock):
        ginfo_mock.return_value = {
            "active_prefix_name": "envName1"
        }
        self.assertEqual("envName1", self.conda.get_active_environment_name())

    @patch('album.core.controller.conda_manager.CondaManager.get_info')
    def test_get_active_environment_path(self, ginfo_mock):
        ginfo_mock.return_value = {
            "active_prefix": "aEnvPath"
        }
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
            with self.assertRaises(EnvironmentError):
                self.conda.create_environment(self.test_environment_name)

            self.assertTrue(self.conda.environment_exists(self.test_environment_name))

            # check if python & pip installed
            self.assertTrue(
                self.conda.is_installed(self.conda.get_environment_path(self.test_environment_name), "python")
            )
            self.assertTrue(
                self.conda.is_installed(self.conda.get_environment_path(self.test_environment_name), "pip")
            )
        else:
            unittest.skip("WARNING - CONDA ERROR!")

    def test_pip_install(self):
        if not self.conda.environment_exists(self.test_environment_name):
            self.conda.create_environment(self.test_environment_name)

        p = self.conda.get_environment_path(self.test_environment_name)
        self.assertIsNotNone(p)

        # check if package NOT installed
        self.assertFalse(self.conda.is_installed(p, "anytree"))

        self.conda.pip_install(p, "anytree")

    def test_pip_install_no_cache(self):
        with patch('album.core.controller.conda_manager.subcommand.run') as run_mock:
            self.conda.pip_install("myEnvironmentPath", "anytree", use_cache=False)

            # expected
            name1, args1, kwargs1 = run_mock.mock_calls[0]

            self.assertIn('--no-cache-dir', args1[0])

    def test_run_script(self):
        with open(self.closed_tmp_file.name, "w") as f:
            f.writelines("print(\"%s\")" % self.test_environment_name)

        p = self.conda.get_active_environment_path()

        self.conda.run_script(p, self.closed_tmp_file.name)

    @unittest.skip("Tested in tear_down() routine!")
    def test_remove_environment(self, active_env_mock):
        pass

    @patch('album.core.utils.subcommand.run', return_value=True)
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

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_set_environment_path(self, gep_mock):
        p = str(self.conda._configuration.cache_path_envs().joinpath(self.test_environment_name))
        gep_mock.return_value = p
        environment = Environment(None, self.test_environment_name, "aPath")
        self.assertIsNone(self.conda.set_environment_path(environment))

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
        environment = Environment(None, "aName", "aPath")
        self.assertTrue(self.conda.is_installed(environment.path(), "python"))
        self.assertTrue(self.conda.is_installed(environment.path(), "python", "3.9.5"))
        self.assertFalse(self.conda.is_installed(environment.path(), "python", "500.1"))
        self.assertTrue(self.conda.is_installed(environment.path(), "python", "2.7"))

    @patch('album.core.controller.conda_manager.CondaManager.run_script', return_value="ranScript")
    def test_run_scripts(self, conda_run_mock):
        script = "print(\"%s\")" % self.test_environment_name
        environment = Environment(None, "aName", "aPath")
        environment._path = "NotNone"

        self.conda.run_scripts(environment, script)
        conda_run_mock.assert_called_once()

    @patch('album.core.controller.conda_manager.CondaManager.run_script', return_value="ranScript")
    def test_run_scripts_no_path(self, conda_run_mock):
        script = "print(\"%s\")" % self.test_environment_name
        environment = Environment(None, "aName", "aPath")
        environment._path = None

        with self.assertRaises(EnvironmentError):
            self.conda.run_scripts(environment, script)
        conda_run_mock.assert_not_called()

    def test_create_or_update_env_no_env(self):
        update_mock = MagicMock()
        create_mock = MagicMock()
        self.conda.update = update_mock
        self.conda.create = create_mock
        environment = Environment(None, "aName", "aPath")

        self.conda.create_or_update_env(environment)

        create_mock.assert_called_once_with(environment)
        update_mock.assert_not_called()

    @patch('album.core.controller.conda_manager.CondaManager.create')
    @patch('album.core.controller.conda_manager.CondaManager.update')
    @patch('album.core.controller.conda_manager.CondaManager.environment_exists')
    def test_create_or_update_env_env_present(self, ex_env_mock, update_mock, create_mock):

        ex_env_mock.return_value = True
        environment = Environment(None, "aName", "aPath")

        self.conda.create_or_update_env(environment)

        update_mock.assert_called_once_with(environment)
        create_mock.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_update(self):
        # ToDo: implement
        pass

    @patch('album.core.controller.conda_manager.CondaManager.create_environment')
    @patch('album.core.controller.conda_manager.CondaManager.create_environment_from_file')
    def test_create_valid_yaml(self, create_environment_from_file_mock, create_environment_mock):
        environment = Environment(None, "aName", "aPath")
        environment._yaml_file = Path("aPath")

        self.conda.create(environment)

        create_environment_from_file_mock.assert_called_once_with(Path("aPath"), "aName")
        create_environment_mock.assert_not_called()

    @patch('album.core.controller.conda_manager.CondaManager.create_environment')
    @patch('album.core.controller.conda_manager.CondaManager.create_environment_from_file')
    def test_create_no_yaml(self, create_environment_from_file_mock, create_environment_mock):
        environment = Environment(None, "aName", "aPath")
        self.conda.create(environment)

        create_environment_mock.assert_called_once_with("aName")
        create_environment_from_file_mock.assert_not_called()

    @patch('album.core.controller.conda_manager.CondaManager.create_or_update_env', return_value="Called")
    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path', return_value="Called")
    @patch('album.core.controller.conda_manager.CondaManager.install_framework', return_value="Called")
    def test_install(self, is_inst_mock, get_env_path_mock, create_mock):
        environment = Environment(None, "aName", "aPath")

        self.conda.install(environment, "TestVersion")

        create_mock.assert_called_once()
        get_env_path_mock.assert_called_once()
        is_inst_mock.assert_called_once_with("Called", "TestVersion")

    @patch('album.core.controller.conda_manager.CondaManager.pip_install')
    @patch('album.core.controller.conda_manager.CondaManager.is_installed', return_value=False)
    def test_install_framework(self, is_installed_mock, pip_install_mock):
        environment = Environment(None, "aName", "aPath")
        environment._path = "NotNone"
        self.conda.install_framework(environment.path(), "version")
        is_installed_mock.assert_called_once_with("NotNone", "album-runner", "version")
        pip_install_mock.assert_called_once()

    @patch('album.core.controller.conda_manager.CondaManager.pip_install')
    def test_pip_install_into_environment(self, conda_install_mock):
        environment = Environment(None, "aName", "aPath")
        environment._path = "aPath"
        self.conda.pip_install_into_environment(environment.path(), "test", "testVersion")

        conda_install_mock.assert_called_once_with("aPath", "test==testVersion", True)


if __name__ == '__main__':
    unittest.main()
