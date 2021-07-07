import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.install_manager import InstallManager
from album.core.controller.resolve_manager import ResolveManager
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestInstallManager(TestUnitCommon):

    def setUp(self):
        self.create_test_config()
        self.create_test_solution_no_env()

        self.install_manager = InstallManager()

    def tearDown(self) -> None:
        super().tearDown()
        InstallManager.instance = None

    def test_install(self):
        # create mocks
        resolve_and_load = MagicMock(return_value=[{"path": Path("aPath"), "catalog": None}, self.active_solution])
        self.install_manager.resolve_manager.resolve_and_load = resolve_and_load

        execute_install_routine = MagicMock(return_value=None)
        self.install_manager._install = execute_install_routine

        add_to_local_catalog = MagicMock(return_value=None)
        self.install_manager.add_to_local_catalog = add_to_local_catalog

        # run
        self.install_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        self.install_manager.install("aPath")

        # assert
        resolve_and_load.assert_called_once()
        execute_install_routine.assert_called_once()
        add_to_local_catalog.assert_called_once()

    @patch('album.core.controller.install_manager.copy_folder', return_value=None)
    def test_add_to_local_catalog(self, copy_folder_mock):
        # create mocks
        add = MagicMock(return_value=None)
        self.test_catalog_collection.local_catalog.add = add

        get_solution_path = MagicMock(return_value="aPath")
        self.test_catalog_collection.local_catalog.get_solution_path = get_solution_path

        clean_resolve_tmp = MagicMock(return_value=None)
        self.install_manager.resolve_manager.clean_resolve_tmp = clean_resolve_tmp

        # run
        self.active_solution.script = ""  # the script gets read during load()
        self.install_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        self.install_manager.add_to_local_catalog(self.active_solution, "aPathToInstall")

        # assert
        add.assert_called_once_with(self.active_solution, force_overwrite=True)
        get_solution_path.assert_called_once_with(
            self.active_solution.group, self.active_solution.name, self.active_solution.version
        )
        copy_folder_mock.assert_called_once_with("aPathToInstall", "aPath", copy_root_folder=False)
        clean_resolve_tmp.assert_called_once()

    def test__install_no_routine(self):
        self.active_solution.environment = EmptyTestClass()

        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_solution.environment.run_scripts = run_script

        environment_install = MagicMock(return_value=None)
        self.active_solution.environment.install = environment_install
        self.active_solution.min_album_version = "test"

        install_dependencies = MagicMock()
        self.install_manager.install_dependencies = install_dependencies

        # run
        self.install_manager.catalog_collection = self.test_catalog_collection

        self.install_manager._install(self.active_solution)

        # assert
        run_script.assert_not_called()
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_solution)

    @patch('album.core.controller.install_manager.create_script', return_value="script")
    def test__install_call_routine(self, create_script_mock):
        self.active_solution.environment = EmptyTestClass()

        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_solution.environment.run_scripts = run_script

        environment_install = MagicMock(return_value=None)
        self.active_solution.environment.install = environment_install
        self.active_solution.min_album_version = "test"

        install_dependencies = MagicMock()
        self.install_manager.install_dependencies = install_dependencies

        # run
        self.active_solution.install = lambda: "notNone"
        self.install_manager.resolve_manager = ResolveManager(self.test_catalog_collection)

        self.install_manager._install(self.active_solution)

        # assert
        create_script_mock.assert_called_once()
        run_script.assert_called_once_with(["script"])
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_solution)

    def test__install_routine_not_callable(self):
        self.active_solution.environment = EmptyTestClass()

        # mocks
        run_script = MagicMock(return_value="aPath")
        self.active_solution.environment.run_scripts = run_script

        environment_install = MagicMock(return_value=None)
        self.active_solution.environment.install = environment_install
        self.active_solution.min_album_version = "test"

        install_dependencies = MagicMock()
        self.install_manager.install_dependencies = install_dependencies

        # run
        self.active_solution.install = "notCallableValue"
        self.install_manager.catalog_collection = self.test_catalog_collection

        self.install_manager._install(self.active_solution)

        # assert
        run_script.assert_not_called()
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_solution)

    def test_install_dependencies_no_deps(self):
        # mocks
        install_dependency = MagicMock(return_value=None)
        self.install_manager.install_dependency = install_dependency

        # run
        self.install_manager.install_dependencies(self.active_solution)

        # assert
        install_dependency.assert_not_called()

    def test_install_dependencies_parent(self):
        # mocks
        install_dependency = MagicMock(return_value=None)
        self.install_manager.install_dependency = install_dependency

        # run
        self.active_solution.parent = "someParent"
        self.install_manager.install_dependencies(self.active_solution)

        # assert
        install_dependency.assert_called_once_with("someParent")

    def test_install_dependency(self):
        # mocks
        resolve_dependency = MagicMock(return_value={"path": "aPath", "catalog": None})
        self.test_catalog_collection.resolve_dependency = resolve_dependency

        install = MagicMock(return_value=None)
        self.install_manager.install = install

        # run
        self.install_manager.resolve_manager.catalog_collection = self.test_catalog_collection
        self.install_manager.install_dependency("something")

        # assert
        resolve_dependency.assert_called_once()
        install.assert_called_once()


if __name__ == '__main__':
    unittest.main()
