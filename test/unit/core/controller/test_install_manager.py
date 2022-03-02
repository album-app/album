import unittest.mock
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch, MagicMock

from album.core.controller.install_manager import InstallManager
from album.core.model.collection_index import CollectionIndex
from album.core.model.resolve_result import ResolveResult
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution
from test.unit.test_unit_core_common import TestUnitCoreCommon, EmptyTestClass


class TestInstallManager(TestUnitCoreCommon):

    def setUp(self):
        super().setUp()
        self.setup_collection()
        self.setup_solution_no_env()
        self.install_manager: InstallManager = self.album_controller.install_manager()
        self.environment_manager = self.album_controller.environment_manager()
        self.assertEqual(self.album_controller, self.install_manager.album)

    def tearDown(self) -> None:
        super().tearDown()

    def test_install(self):
        # create mocks
        resolve_result = ResolveResult(
            path=Path("aPath"),
            catalog=self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates()
        )

        _install_resolve_result = MagicMock(return_value=None)
        self.install_manager._install_resolve_result = _install_resolve_result

        # call
        self.install_manager.install(resolve_result, [])

        # assert
        _install_resolve_result.assert_called_once_with(resolve_result, [], parent=False)

    @unittest.skip("Needs to be implemented!")
    def test__resolve_result_is_installed(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__install_resolve_result(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test__register(self):
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
        self.environment_manager.install_environment = install_environment

        set_environment = MagicMock(return_value=None)
        self.environment_manager.set_environment = set_environment

        run_solution_install_routine = MagicMock()
        self.install_manager._run_solution_install_routine = run_solution_install_routine

        # call
        self.install_manager._install_active_solution(
            ResolveResult("", self.album_controller.collection_manager().catalogs().get_cache_catalog(), None,
                          self.active_solution.coordinates(), self.active_solution), ["myargs"]
        )

        # assert
        run_solution_install_routine.assert_called_once_with(self.active_solution, None, ["myargs"])
        set_environment.assert_not_called()
        install_environment.assert_called_once()

    def test__install_active_solution_with_parent(self):
        self.active_solution._setup.album_api_version = "test"

        self.parent_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        self.parent_solution.environment = lambda: EmptyTestClass()  # different object in memory

        self.active_solution._setup.dependencies = {"parent": "aParent"}

        # mocks
        install_environment = MagicMock(return_value=None)
        self.environment_manager.install_environment = install_environment

        set_environment = MagicMock(return_value=None)
        self.environment_manager.set_environment = set_environment

        parent_resolve_result = ResolveResult(None, None, None, None, loaded_solution=self.parent_solution)
        _install_parent = MagicMock(return_value=parent_resolve_result)
        self.install_manager._install_parent = _install_parent
        _set_parent = MagicMock()
        self.install_manager._set_parent = _set_parent

        run_solution_install_routine = MagicMock()
        self.install_manager._run_solution_install_routine = run_solution_install_routine

        # call
        self.install_manager._install_active_solution(
            ResolveResult("", self.album_controller.collection_manager().catalogs().get_cache_catalog(), None,
                          self.active_solution.coordinates(), self.active_solution), ["myargs"]
        )

        # assert
        _install_parent.assert_called_once_with("aParent")
        run_solution_install_routine.assert_called_once_with(self.active_solution, set_environment.return_value,
                                                             ["myargs"])
        set_environment.assert_called_once()
        install_environment.assert_not_called()

    @unittest.skip("Needs to be implemented!")
    def test_run_solution_install_routine(self):
        # TODO implement
        pass

    @patch('album.core.controller.install_manager.build_resolve_string', return_value="myResolveString")
    def test__install_parent(self, build_resolve_string_mock):
        # mocks
        _install = MagicMock(return_value=None)
        self.install_manager._install_resolve_result = _install
        resolve = MagicMock(return_value="resolve")
        self.album_controller.collection_manager().resolve_and_load = resolve

        # call
        self.install_manager._install_parent({"myDictKey": "myDeps"})

        # asert
        _install.assert_called_once_with("resolve", parent=True)
        resolve.assert_called_once()
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
    def test_run_solution_uninstall_routine(self):
        # TODO implement
        pass

    @unittest.skip("Needs to be implemented!")
    def test_remove_dependencies(self):
        # TODO implement
        pass

    @patch('album.core.controller.install_manager.dict_to_coordinates', return_value=Coordinates('g1', 'n1', 'v1'))
    @patch('album.core.controller.install_manager.get_parent_dict', return_value=False)
    @patch('album.core.controller.install_manager.remove_disc_content_from_solution')
    def test_clean_unfinished_installations_env_exists(self, remove_dc, _, __):
        # mocks
        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = set_cache_paths
        get_unfinished_installation_solutions = MagicMock(
            return_value=[CollectionIndex.CollectionSolution(
                {'group': 'g1', 'name': 'n1', 'version': 'v1'},  # setup
                {'catalog_id': 1}  # internal
            )]
        )
        self.album_controller.collection_manager().get_collection_index().get_unfinished_installation_solutions = get_unfinished_installation_solutions

        get_by_id_mock = MagicMock(return_value=self.album_controller.collection_manager().catalogs().get_cache_catalog())
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = retrieve_and_load_resolve_result

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = _clean_unfinished_installations_environment

        set_uninstalled = MagicMock()
        self.album_controller.collection_manager().solutions().set_uninstalled = set_uninstalled

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_called_once()
        set_cache_paths.assert_called_once()
        get_by_id_mock.assert_called_once_with(1)
        retrieve_and_load_resolve_result.assert_called_once()
        _clean_unfinished_installations_environment.assert_called_once()
        set_uninstalled.assert_called_once()

    @patch('album.core.controller.install_manager.dict_to_coordinates', return_value=Coordinates('g1', 'n1', 'v1'))
    @patch('album.core.controller.install_manager.get_parent_dict', return_value=True)
    @patch('album.core.controller.install_manager.remove_disc_content_from_solution')
    def test_clean_unfinished_installations_parent(self, remove_dc, _, __):
        # mocks
        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = set_cache_paths
        get_unfinished_installation_solutions = MagicMock(
            return_value=[CollectionIndex.CollectionSolution(
                {'group': 'g1', 'name': 'n1', 'version': 'v1'},  # setup
                {'catalog_id': 1}  # internal
            )]
        )
        self.album_controller.collection_manager().get_collection_index().get_unfinished_installation_solutions = get_unfinished_installation_solutions

        get_by_id_mock = MagicMock(return_value=self.album_controller.collection_manager().catalogs().get_cache_catalog())
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = retrieve_and_load_resolve_result

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = _clean_unfinished_installations_environment

        set_uninstalled = MagicMock()
        self.album_controller.collection_manager().solutions().set_uninstalled = set_uninstalled

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_called_once()
        set_cache_paths.assert_called_once()
        get_by_id_mock.assert_called_once_with(1)
        retrieve_and_load_resolve_result.assert_called_once()
        _clean_unfinished_installations_environment.assert_not_called()
        set_uninstalled.assert_called_once()

    @patch('album.core.controller.install_manager.remove_disc_content_from_solution')
    def test_clean_unfinished_installations_empty(self, remove_dc):

        # mocks
        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = set_cache_paths
        get_by_id_mock = MagicMock(return_value=self.album_controller.collection_manager().catalogs().get_cache_catalog())
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = retrieve_and_load_resolve_result

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = _clean_unfinished_installations_environment

        set_uninstalled = MagicMock()
        self.album_controller.collection_manager().solutions().set_uninstalled = set_uninstalled

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_not_called()
        set_cache_paths.assert_not_called()
        get_by_id_mock.assert_not_called()
        retrieve_and_load_resolve_result.assert_not_called()
        _clean_unfinished_installations_environment.assert_not_called()
        set_uninstalled.assert_not_called()

    def test__clean_unfinished_installations_environment_env_deleted(self):
        # mocks
        set_environment = MagicMock(return_value="myEnv")
        self.environment_manager.set_environment = set_environment

        remove_environment = MagicMock(return_value=True)
        self.environment_manager.remove_environment = remove_environment

        _remove_environment_link = MagicMock()
        self.install_manager._remove_environment_link = _remove_environment_link

        # prepare
        r = ResolveResult("mypath", None, None, None)
        # call
        self.install_manager._clean_unfinished_installations_environment(r)

        # assert
        set_environment.assert_called_once()
        remove_environment.assert_called_once_with("myEnv")

    def test__clean_unfinished_installations_environment_env_not_deleted(self):
        c = EmptyTestClass()
        c.name = lambda: "myName"

        # mocks
        set_environment = MagicMock(return_value="myEnv")
        self.environment_manager.set_environment = set_environment

        remove_environment = MagicMock(return_value=False)
        self.environment_manager.remove_environment = remove_environment

        # prepare
        r = ResolveResult("mypath", c, None, Coordinates("a", "b", "c"))
        # call
        self.install_manager._clean_unfinished_installations_environment(r)

        # assert
        set_environment.assert_called_once()
        remove_environment.assert_called_once_with("myEnv")


if __name__ == '__main__':
    unittest.main()
