import unittest.mock
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.controller.install_manager import InstallManager
from album.core.model.resolve_result import ResolveResult
from test.unit.test_unit_common import TestUnitCommon, EmptyTestClass


class TestInstallManager(TestUnitCommon):

    def setUp(self):
        super().setUp()
        self.create_album_test_instance()
        self.create_test_solution_no_env()
        self.install_manager = InstallManager()

    def tearDown(self) -> None:
        super().tearDown()

    def test__install(self):
        # create mocks
        resolve_result = ResolveResult(
            path=Path("aPath"),
            catalog=self.collection_manager.catalogs().get_local_catalog(),
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates
        )

        resolve_and_load = MagicMock(
            return_value=resolve_result
        )
        self.collection_manager.resolve_download_and_load = resolve_and_load

        _install_resolve_result = MagicMock(return_value=None)
        self.install_manager._install_resolve_result = _install_resolve_result

        # call
        self.install_manager._install("aPath", [])

        # assert
        resolve_and_load.assert_called_once()
        _install_resolve_result.assert_called_once_with(resolve_result, [], False)

    @unittest.skip("Needs to be implemented!")
    def test_install_from_catalog_coordinates(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__install_from_catalog_coordinates(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_install_from_coordinates(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__install_from_coordinates(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__resolve_result_is_installed(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__install_resolve_result(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_set_parent(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_update_in_collection_index(self):
        # TODO implement
        pass

    def test__install_active_solution(self):
        self.active_solution.environment = EmptyTestClass()

        # mocks
        install_environment = MagicMock(return_value=None)
        self.install_manager.environment_manager.install_environment = install_environment

        set_environment = MagicMock(return_value=None)
        self.install_manager.environment_manager.set_environment = set_environment

        run_solution_install_routine = MagicMock()
        self.install_manager.run_solution_install_routine = run_solution_install_routine

        # call
        self.install_manager._install_active_solution(
            self.active_solution, self.collection_manager.catalogs().get_local_catalog(), ["myargs"]
        )

        # assert
        run_solution_install_routine.assert_called_once_with(self.active_solution, ["myargs"])
        set_environment.assert_not_called()
        install_environment.assert_called_once()

    def test__install_active_solution_with_parent(self):
        self.active_solution.min_album_version = "test"

        self.parent_solution = deepcopy(self.active_solution)
        self.parent_solution.environment = EmptyTestClass()  # different object in memory

        self.active_solution.parent = "aParent"

        # mocks
        install_environment = MagicMock(return_value=None)
        self.install_manager.environment_manager.install_environment = install_environment

        set_environment = MagicMock(return_value=None)
        self.install_manager.environment_manager.set_environment = set_environment

        parent_resolve_result = ResolveResult(None, None, None, None, loaded_solution=self.parent_solution)
        _install_parent = MagicMock(return_value=parent_resolve_result)
        self.install_manager._install_parent = _install_parent

        run_solution_install_routine = MagicMock()
        self.install_manager.run_solution_install_routine = run_solution_install_routine

        # call
        self.install_manager._install_active_solution(
            self.active_solution, self.collection_manager.catalogs().get_local_catalog(), ["myargs"]
        )

        # assert
        _install_parent.assert_called_once_with("aParent")
        run_solution_install_routine.assert_called_once_with(self.active_solution, ["myargs"])
        set_environment.assert_called_once()
        install_environment.assert_not_called()

    @patch('album.core.controller.install_manager.build_resolve_string', return_value="myResolveString")
    def test__install_parent(self, build_resolve_string_mock):
        # mocks
        _install = MagicMock(return_value=None)
        self.install_manager._install = _install

        # call
        self.install_manager._install_parent({"myDictKey": "myDeps"})

        # assert
        _install.assert_called_once_with("myResolveString", parent=True)
        build_resolve_string_mock.assert_called_once_with({"myDictKey": "myDeps"})

    @unittest.skip("Needs to be implemented!")
    def test_uninstall(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__uninstall(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_dependencies(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_disc_content(self):
        # TODO implement
        pass


if __name__ == '__main__':
    unittest.main()
