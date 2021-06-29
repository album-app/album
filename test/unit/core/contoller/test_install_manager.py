import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from hips.core.controller.install_manager import InstallManager
from test.unit.test_common import TestHipsCommon


class TestInstallManager(TestHipsCommon):

    def setUp(self):
        self.create_test_config()
        self.create_test_hips_no_env()

        with patch.object(InstallManager, '__init__', return_value=None) as init_mock:
            InstallManager.instance = None
            self.hips_installer = InstallManager()
            init_mock.assert_called_once()

    def tearDown(self) -> None:
        super().tearDown()
        InstallManager.instance = None

    @patch('hips.core.controller.install_manager.load')
    def test_install(self, load_mock):
        # create mocks
        load_mock.return_value = self.active_hips

        resolve_from_str = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.test_catalog_collection.resolve_from_str = resolve_from_str

        execute_install_routine = MagicMock(return_value=None)
        self.hips_installer._install = execute_install_routine

        add_to_local_catalog = MagicMock(return_value=None)
        self.hips_installer.add_to_local_catalog = add_to_local_catalog

        # run
        self.hips_installer.catalog_collection = self.test_catalog_collection
        self.hips_installer.install("aPath")

        # assert
        resolve_from_str.assert_called_once()
        execute_install_routine.assert_called_once()
        add_to_local_catalog.assert_called_once()

    @patch('hips.core.controller.install_manager.copy_in_file', return_value=None)
    def test_add_to_local_catalog(self, copy_file_mock):
        # create mocks
        add = MagicMock(return_value=None)
        self.test_catalog_collection.local_catalog.add = add

        get_solution_cache_file = MagicMock(return_value="aPath")
        self.test_catalog_collection.local_catalog.get_solution_cache_file = get_solution_cache_file

        # run
        self.active_hips.script = ""  # the script gets read during load()
        self.hips_installer.catalog_collection = self.test_catalog_collection
        self.hips_installer.add_to_local_catalog(self.active_hips)

        # assert
        add.assert_called_once_with(self.active_hips, force_overwrite=True)
        get_solution_cache_file.assert_called_once_with(
            self.active_hips.group, self.active_hips.name, self.active_hips.version
        )
        copy_file_mock.assert_called_once_with(self.active_hips.script, "aPath")

    def test__install_no_routine(self):
        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_hips.environment.run_scripts = run_script

        environment_install = MagicMock(return_value=None)
        self.active_hips.environment.install = environment_install
        self.active_hips.min_hips_version = "test"

        install_dependencies = MagicMock()
        self.hips_installer.install_dependencies = install_dependencies

        # run
        self.hips_installer.catalog_collection = self.test_catalog_collection

        self.hips_installer._install(self.active_hips)

        # assert
        run_script.assert_not_called()
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_hips)

    @patch('hips.core.controller.install_manager.create_script', return_value="script")
    def test__install_call_routine(self, create_script_mock):
        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_hips.environment.run_scripts = run_script

        environment_install = MagicMock(return_value=None)
        self.active_hips.environment.install = environment_install
        self.active_hips.min_hips_version = "test"

        install_dependencies = MagicMock()
        self.hips_installer.install_dependencies = install_dependencies

        # run
        self.active_hips.install = lambda: "notNone"
        self.hips_installer.catalog_collection = self.test_catalog_collection

        self.hips_installer._install(self.active_hips)

        # assert
        create_script_mock.assert_called_once()
        run_script.assert_called_once_with(["script"])
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_hips)

    def test__install_routine_not_callable(self):
        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_hips.environment.run_scripts = run_script

        environment_install = MagicMock(return_value=None)
        self.active_hips.environment.install = environment_install
        self.active_hips.min_hips_version = "test"

        install_dependencies = MagicMock()
        self.hips_installer.install_dependencies = install_dependencies

        # run
        self.active_hips.install = "notCallableValue"
        self.hips_installer.catalog_collection = self.test_catalog_collection

        self.hips_installer._install(self.active_hips)

        # assert
        run_script.assert_not_called()
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_hips)

    def test_install_dependencies_no_deps(self):
        # mocks
        install_dependency = MagicMock(return_value=None)
        self.hips_installer.install_dependency = install_dependency

        # run
        self.hips_installer.install_dependencies(self.active_hips)

        # assert
        install_dependency.assert_not_called()

    def test_install_dependencies_parent(self):
        # mocks
        install_dependency = MagicMock(return_value=None)
        self.hips_installer.install_dependency = install_dependency

        # run
        self.active_hips.parent = "someParent"
        self.hips_installer.install_dependencies(self.active_hips)

        # assert
        install_dependency.assert_called_once_with("someParent")

    def test_install_dependency(self):
        # mocks
        resolve_hips_dependency = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.test_catalog_collection.resolve_hips_dependency = resolve_hips_dependency

        install = MagicMock(return_value=None)
        self.hips_installer.install = install

        # run
        self.hips_installer.catalog_collection = self.test_catalog_collection
        self.hips_installer.install_dependency("something")

        # assert
        resolve_hips_dependency.assert_called_once()
        install.assert_called_once()


if __name__ == '__main__':
    unittest.main()
