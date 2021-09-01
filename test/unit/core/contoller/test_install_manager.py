import unittest.mock
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from album.core.controller.install_manager import InstallManager
from album.core.model.catalog import Catalog
from album.core.model.resolve_result import ResolveResult
from album.core.model.group_name_version import GroupNameVersion
from album.core.utils.operations.resolve_operations import solution_to_group_name_version
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestInstallManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_test_config()
        self.create_test_solution_no_env()
        self.create_test_catalog_manager()
        self.install_manager = InstallManager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_install(self):
        # create mocks
        resolve_and_load = MagicMock(
            return_value= ResolveResult(path=Path("aPath"), catalog=self.collection_manager.catalogs().get_local_catalog(), active_solution=self.active_solution)
        )
        self.collection_manager.resolve_download_and_load = resolve_and_load

        execute_install_routine = MagicMock(return_value=None)
        self.install_manager._install = execute_install_routine

        add_to_local_catalog = MagicMock(return_value=None)
        self.install_manager.collection_manager.add_solution_to_local_catalog = add_to_local_catalog

        update_in_collection_index = MagicMock(return_value=None)
        self.install_manager.update_in_collection_index = update_in_collection_index

        # run
        self.install_manager.install("aPath")

        # assert
        resolve_and_load.assert_called_once()
        execute_install_routine.assert_called_once()
        add_to_local_catalog.assert_called_once_with(self.active_solution, Path("aPath").parent)
        update_in_collection_index.assert_not_called()

    @patch('album.core.model.collection_index.CollectionIndex.get_solution')
    @patch('album.core.controller.collection.solution_handler.SolutionHandler.update_solution')
    @patch('album.core.controller.collection.catalog_handler.CatalogHandler.get_by_id', return_value=Catalog("cat_id", "", ""))
    def test_add_to_solutions_db_no_parent(self, get_by_id_mock, update_solution_mock, get_solution_mock):
        update_solution_mock.return_value = None

        self.install_manager.update_in_collection_index("cat_id", None, self.active_solution)

        update_solution_mock.assert_called_once_with(
            get_by_id_mock.return_value, solution_to_group_name_version(self.active_solution), self.active_solution.get_deploy_dict()
        )
        get_solution_mock.assert_not_called()

    @patch('album.core.model.collection_index.CollectionIndex.get_solution_by_catalog_grp_name_version')
    @patch('album.core.controller.collection.solution_handler.SolutionHandler.update_solution')
    @patch('album.core.controller.collection.catalog_handler.CatalogHandler.get_by_id', return_value=Catalog("cat_id", "", ""))
    def test_add_to_solutions_db_parent(self, get_by_id_mock, update_solution_mock, get_solution_mock):
        update_solution_mock.return_value = None
        get_solution_mock.return_value = {"solution_id": 100}

        self.active_solution.parent = {"group": "grp", "name": "pName", "version": "pVersion"}

        self.install_manager.update_in_collection_index("cat_id", "cat_parent_id", self.active_solution)

        #FIXME currently not checking for parent information to be added
        update_solution_mock.assert_called_once_with(
            get_by_id_mock.return_value, solution_to_group_name_version(self.active_solution), self.active_solution.get_deploy_dict()
        )
        get_solution_mock.assert_called_once_with("cat_parent_id", GroupNameVersion("grp", "pName", "pVersion"))

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
        self.install_manager._install(self.active_solution)

        # assert
        run_script.assert_not_called()
        environment_install.assert_called_once()
        install_dependencies.assert_called_once_with(self.active_solution)

    @patch('album.core.controller.install_manager.create_solution_script', return_value="script")
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
        resolve_dependency = MagicMock(return_value=ResolveResult(path="aPath", catalog=None))
        self.install_manager.collection_manager.resolve_dependency = resolve_dependency

        install = MagicMock(return_value=None)
        self.install_manager.install = install

        # run
        self.install_manager.install_dependency("something")

        # assert
        resolve_dependency.assert_called_once()
        install.assert_called_once()


if __name__ == '__main__':
    unittest.main()
