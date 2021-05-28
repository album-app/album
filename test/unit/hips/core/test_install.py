import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from hips.core.install import HipsInstaller
from test.unit.test_common import TestHipsCommon


class TestHipsInstaller(TestHipsCommon):

    def setUp(self):
        self.create_test_config()
        self.create_test_hips_no_env()

        with patch.object(HipsInstaller, '__init__', return_value=None) as init_mock:
            self.hips_installer = HipsInstaller()
            init_mock.assert_called_once()

    def tearDown(self) -> None:
        super().tearDown()

    @patch('hips.core.install.load')
    def test_install(self, load_mock):
        class Args:
            def __init__(self, p):
                self.path = p

        # create mocks
        install = MagicMock(return_value=None)
        self.active_hips.environment.install = install
        self.active_hips.min_hips_version = "test"

        load_mock.return_value = self.active_hips

        resolve_from_str = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.config.resolve_from_str = resolve_from_str

        install_dependencies = MagicMock(return_value=None)
        self.hips_installer.install_dependencies = install_dependencies

        execute_install_routine = MagicMock(return_value=None)
        self.hips_installer.execute_install_routine = execute_install_routine

        add_to_local_catalog = MagicMock(return_value=None)
        self.hips_installer.add_to_local_catalog = add_to_local_catalog

        # run
        self.hips_installer.catalog_configuration = self.config
        self.hips_installer.install(args=Args("aPath"))

        # assert
        install.assert_called_once()
        resolve_from_str.assert_called_once()
        install_dependencies.assert_called_once()
        execute_install_routine.assert_called_once()
        add_to_local_catalog.assert_called_once()

    @patch('hips.core.install.copy_in_file', return_value=None)
    def test_add_to_local_catalog(self, copy_file_mock):
        # create mocks
        add = MagicMock(return_value=None)
        self.config.local_catalog.add = add

        get_solution_cache_file = MagicMock(return_value="aPath")
        self.config.local_catalog.get_solution_cache_file = get_solution_cache_file

        # run
        self.active_hips.script = ""  # the script gets read during load()
        self.hips_installer.active_hips = self.active_hips
        self.hips_installer.catalog_configuration = self.config
        self.hips_installer.add_to_local_catalog()

        # assert
        add.assert_called_once_with(self.active_hips, force_overwrite=True)
        get_solution_cache_file.assert_called_once_with(
            self.active_hips.group, self.active_hips.name, self.active_hips.version
        )
        copy_file_mock.assert_called_once_with(self.active_hips.script, "aPath")

    def test_execute_install_routine_no_routine(self):
        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_hips.environment.run_script = run_script

        # run
        self.hips_installer.active_hips = self.active_hips
        self.hips_installer.catalog_configuration = self.config

        self.hips_installer.execute_install_routine()

        # assert
        run_script.assert_not_called()

    @patch('hips.core.install.create_script', return_value="script")
    def test_execute_install_routine_call_routine(self, create_script_mock):
        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_hips.environment.run_script = run_script

        # run
        self.active_hips.install = lambda: "notNone"
        self.hips_installer.active_hips = self.active_hips
        self.hips_installer.catalog_configuration = self.config

        self.hips_installer.execute_install_routine()

        # assert
        create_script_mock.assert_called_once()
        run_script.assert_called_once_with("script")

    def test_execute_install_routine_routine_not_callable(self):
        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_hips.environment.run_script = run_script

        # run
        self.active_hips.install = "notCallableValue"
        self.hips_installer.active_hips = self.active_hips
        self.hips_installer.catalog_configuration = self.config

        self.hips_installer.execute_install_routine()

        # assert
        run_script.assert_not_called()

    def test_install_dependencies_no_deps(self):
        # mocks
        install_dependency = MagicMock(return_value=None)
        self.hips_installer.install_dependency = install_dependency

        # run
        self.hips_installer.active_hips = self.active_hips
        self.hips_installer.install_dependencies()

        # assert
        install_dependency.assert_not_called()

    def test_install_dependencies_parent(self):
        # mocks
        install_dependency = MagicMock(return_value=None)
        self.hips_installer.install_dependency = install_dependency

        # run
        self.active_hips.parent = "someParent"
        self.hips_installer.active_hips = self.active_hips
        self.hips_installer.install_dependencies()

        # assert
        install_dependency.assert_called_once_with("someParent")

    @patch('hips.core.install.install', return_value=None)
    def test_install_dependency(self, install):
        # mocks
        resolve_hips_dependency = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.config.resolve_hips_dependency = resolve_hips_dependency

        # run
        self.hips_installer.catalog_configuration = self.config
        self.hips_installer.install_dependency("something")

        # assert
        resolve_hips_dependency.assert_called_once()
        install.assert_called_once()


if __name__ == '__main__':
    unittest.main()
