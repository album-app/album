import unittest.mock
from copy import deepcopy
from pathlib import Path
from test.unit.test_unit_core_common import EmptyTestClass, TestUnitCoreCommon
from unittest.mock import MagicMock, patch

from album.core.controller.install_manager import InstallManager
from album.core.model.collection_index import CollectionIndex
from album.core.model.resolve_result import ResolveResult
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution


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
            catalog=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog(),
            loaded_solution=self.active_solution,
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
        )

        _install_resolve_result = MagicMock(return_value=None)
        self.install_manager._install_loaded_resolve_result = _install_resolve_result

        resolve = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve_and_load = resolve

        # call
        self.install_manager.install("aPath", False, [])

        # assert
        _install_resolve_result.assert_called_once_with(
            resolve_result, parent=False, allow_recursive=False
        )

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
        user_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().user_cache_path = user_cache_path

        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().internal_cache_path = internal_cache_path

        package_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().app_path = package_path

        data_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().data_path = data_path

        install_environment = MagicMock(return_value=None)
        self.environment_manager.install_environment = install_environment

        set_environment = MagicMock(return_value=None)
        self.environment_manager.set_environment = set_environment

        run_solution_install_routine = MagicMock()
        self.install_manager._run_solution_install_routine = (
            run_solution_install_routine
        )

        r = ResolveResult(
            path=Path(""),
            catalog=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog(),
            collection_entry=None,
            coordinates=self.active_solution.coordinates(),
            loaded_solution=self.active_solution,
        )

        # call
        self.install_manager._install_active_solution(r)

        # assert
        run_solution_install_routine.assert_called_once_with(r)
        set_environment.assert_not_called()
        install_environment.assert_called_once()
        user_cache_path.assert_called_once()
        internal_cache_path.assert_called_once()
        package_path.assert_called_once()
        data_path.assert_called_once()

    def test__install_active_solution_with_parent(self):
        self.active_solution._setup.album_api_version = "1.0.1"

        self.parent_solution = Solution(deepcopy(dict(self.active_solution.setup())))
        self.parent_solution.environment = (
            lambda: EmptyTestClass()
        )  # different object in memory

        self.active_solution._setup.dependencies = {"parent": "aParent"}

        # mocks
        user_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().user_cache_path = user_cache_path

        internal_cache_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().internal_cache_path = internal_cache_path

        package_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().app_path = package_path

        data_path = MagicMock(return_value=Path(self.tmp_dir.name))
        self.active_solution.installation().data_path = data_path

        install_environment = MagicMock(return_value=None)
        self.environment_manager.install_environment = install_environment

        parent_resolve_result = ResolveResult(
            Path(""),
            None,
            CollectionIndex.CollectionSolution(),
            None,
            loaded_solution=self.parent_solution,
        )
        _install_parent = MagicMock(return_value=parent_resolve_result)
        self.install_manager._install_parent = _install_parent

        self.album_controller.solutions().set_parent = MagicMock()

        run_solution_install_routine = MagicMock()
        self.install_manager._run_solution_install_routine = (
            run_solution_install_routine
        )

        self.album_controller.collection_manager().get_collection_index().get_solution_by_catalog_grp_name_version = MagicMock(
            return_value=CollectionIndex.CollectionSolution()
        )

        r = ResolveResult(
            Path(""),
            self.album_controller.collection_manager().catalogs().get_cache_catalog(),
            CollectionIndex.CollectionSolution(),
            self.active_solution.coordinates(),
            self.active_solution,
        )

        # call
        self.install_manager._install_active_solution(r)

        # assert
        _install_parent.assert_called_once_with(
            "aParent", "1.0.1", Coordinates("tsg", "tsn", "tsv")
        )
        run_solution_install_routine.assert_called_once_with(r)
        install_environment.assert_not_called()

        user_cache_path.assert_called_once()
        internal_cache_path.assert_called_once()
        package_path.assert_called_once()
        data_path.assert_called_once()

    @unittest.skip("Needs to be implemented!")
    def test_run_solution_install_routine(self):
        # TODO implement
        pass

    @patch(
        "album.core.controller.install_manager.build_resolve_string",
        return_value="myResolveString",
    )
    def test__install_parent(self, build_resolve_string_mock):
        # mocks
        _install = MagicMock(return_value=None)
        self.install_manager._install_loaded_resolve_result = _install

        s = Solution(
            {
                "group": "myGroup",
                "name": "myName",
                "version": "myVersion",
            }
        )

        class R:
            album_api_version = "5.1.0"

        s._setup = R()
        r = ResolveResult(
            "", None, None, Coordinates("myGroup", "myName", "myVersion"), s
        )

        resolve = MagicMock(return_value=r)
        self.album_controller.collection_manager().resolve_and_load = resolve

        # call
        self.install_manager._install_parent(
            {"myDictKey": "myDeps"}, "5.1.0", Coordinates("a", "b", "c")
        )

        # asert
        _install.assert_called_once_with(r, parent=True)
        resolve.assert_called_once()
        build_resolve_string_mock.assert_called_once_with({"myDictKey": "myDeps"})

    @patch(
        "album.core.controller.install_manager.build_resolve_string",
        return_value="myResolveString",
    )
    def test__install_parent_eq_child(self, build_resolve_string_mock):
        # mocks
        _install = MagicMock(return_value=None)
        self.install_manager._install_loaded_resolve_result = _install

        s = Solution(
            {
                "group": "myGroup",
                "name": "myName",
                "version": "myVersion",
            }
        )

        class R:
            album_api_version = "5.1.0"

        s._setup = R()
        r = ResolveResult(
            "", None, None, Coordinates("myGroup", "myName", "myVersion"), s
        )

        resolve = MagicMock(return_value=r)
        self.album_controller.collection_manager().resolve_and_load = resolve

        # call
        with self.assertRaises(ValueError):
            self.install_manager._install_parent(
                {"myDictKey": "myDeps"}, "5.1.0", s.coordinates()
            )

    @unittest.skip("Needs to be implemented!")
    def test_uninstall(self):
        # TODO implement
        pass

    def _prepare_uninstall(self, load_error=None, parent=None):
        # an installed solution as it is stored in the collection
        collection_entry = CollectionIndex.CollectionSolution(
            {"group": "tsg", "name": "tsn", "version": "tsv"},  # setup
            {"parent": parent, "children": []},  # internal
        )
        resolve_result = ResolveResult(
            path=Path(self.tmp_dir.name).joinpath("solution.py"),
            catalog=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog(),
            collection_entry=collection_entry,
            coordinates=Coordinates("tsg", "tsn", "tsv"),
        )

        # mocks
        if load_error:
            resolve_installed_and_load = MagicMock(side_effect=load_error)
        else:
            resolve_installed_and_load = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve_installed_and_load = (
            resolve_installed_and_load
        )

        resolve_installed = MagicMock(return_value=resolve_result)
        self.album_controller.collection_manager().resolve_installed = resolve_installed

        self.set_environment = MagicMock(return_value="myEnv")
        self.environment_manager.set_environment = self.set_environment

        self.remove_environment = MagicMock(return_value=True)
        self.environment_manager.remove_environment = self.remove_environment

        self.run_solution_uninstall_routine = MagicMock()
        self.install_manager._run_solution_uninstall_routine = (
            self.run_solution_uninstall_routine
        )

        self.remove_solution = MagicMock()
        self.album_controller.solutions().remove_solution = self.remove_solution

        self.install_manager._remove_disc_content_from_solution = MagicMock()

        return resolve_result

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_loaded(self, remove_disc_content_from_environment):
        r = self._prepare_uninstall()

        # call
        self.install_manager.uninstall("tsg:tsn:tsv")

        # assert
        self.set_environment.assert_called_once_with(r)
        self.run_solution_uninstall_routine.assert_called_once_with(r)
        self.remove_environment.assert_called_once_with("myEnv")
        remove_disc_content_from_environment.assert_called_once_with("myEnv")
        self.remove_solution.assert_called_once_with(r.catalog(), r.coordinates())

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_solution_cannot_be_loaded(
        self, remove_disc_content_from_environment
    ):
        # no setup() call in the file, file missing, file broken
        for load_error in [
            ValueError("Cannot load solution!"),
            FileNotFoundError("solution.py"),
            SyntaxError("invalid syntax"),
        ]:
            with self.subTest(load_error=type(load_error).__name__):
                remove_disc_content_from_environment.reset_mock()
                r = self._prepare_uninstall(load_error=load_error)

                # call
                self.install_manager.uninstall("tsg:tsn:tsv")

                # assert
                self.set_environment.assert_called_once_with(r)
                self.run_solution_uninstall_routine.assert_not_called()
                self.remove_environment.assert_called_once_with("myEnv")
                remove_disc_content_from_environment.assert_called_once_with("myEnv")
                self.remove_solution.assert_called_once_with(
                    r.catalog(), r.coordinates()
                )

    @patch(
        "album.core.controller.install_manager.EnvironmentManager.remove_disc_content_from_environment"
    )
    def test_uninstall_solution_cannot_be_loaded_parent(
        self, remove_disc_content_from_environment
    ):
        # the solution runs in the environment of its parent, which must be kept
        r = self._prepare_uninstall(
            load_error=ValueError("Cannot load solution!"),
            parent=CollectionIndex.CollectionSolution(),
        )

        # call
        self.install_manager.uninstall("tsg:tsn:tsv")

        # assert
        self.run_solution_uninstall_routine.assert_not_called()
        self.remove_environment.assert_not_called()
        remove_disc_content_from_environment.assert_not_called()
        self.remove_solution.assert_called_once_with(r.catalog(), r.coordinates())

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

    @patch(
        "album.core.controller.install_manager.dict_to_coordinates",
        return_value=Coordinates("g1", "n1", "v1"),
    )
    def test_clean_unfinished_installations_env_exists(self, _):
        # mocks
        remove_dc = MagicMock()
        self.album_controller.install_manager()._remove_disc_content_from_solution = (
            remove_dc
        )

        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            set_cache_paths
        )
        get_unfinished_installation_solutions = MagicMock(
            return_value=[
                CollectionIndex.CollectionSolution(
                    {"group": "g1", "name": "n1", "version": "v1"},  # setup
                    {"catalog_id": 1, "parent": None},  # internal
                )
            ]
        )
        self.album_controller.collection_manager().get_collection_index().get_unfinished_installation_solutions = (
            get_unfinished_installation_solutions
        )

        get_by_id_mock = MagicMock(
            return_value=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
        )
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = (
            _clean_unfinished_installations_environment
        )

        remove_solution = MagicMock()
        self.album_controller.collection_manager().solutions().remove_solution = (
            remove_solution
        )

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_called_once()
        set_cache_paths.assert_called_once()
        get_by_id_mock.assert_called_once_with(1)
        retrieve_and_load_resolve_result.assert_not_called()
        _clean_unfinished_installations_environment.assert_called_once()
        remove_solution.assert_called_once()

    @patch(
        "album.core.controller.install_manager.dict_to_coordinates",
        return_value=Coordinates("g1", "n1", "v1"),
    )
    def test_clean_unfinished_installations_parent(self, _):
        parent_entry = CollectionIndex.CollectionSolution(
            {"group": "g0", "name": "n0", "version": "v0"}, {"catalog_id": 1}
        )

        # mocks
        remove_dc = MagicMock()
        self.album_controller.install_manager()._remove_disc_content_from_solution = (
            remove_dc
        )

        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            set_cache_paths
        )
        get_unfinished_installation_solutions = MagicMock(
            return_value=[
                CollectionIndex.CollectionSolution(
                    {"group": "g1", "name": "n1", "version": "v1"},  # setup
                    {"catalog_id": 1, "parent": parent_entry},  # internal
                )
            ]
        )
        self.album_controller.collection_manager().get_collection_index().get_unfinished_installation_solutions = (
            get_unfinished_installation_solutions
        )

        get_by_id_mock = MagicMock(
            return_value=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
        )
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = (
            _clean_unfinished_installations_environment
        )

        remove_solution = MagicMock()
        self.album_controller.collection_manager().solutions().remove_solution = (
            remove_solution
        )

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        remove_dc.assert_called_once()
        set_cache_paths.assert_called_once()
        get_by_id_mock.assert_called_once_with(1)
        retrieve_and_load_resolve_result.assert_not_called()
        _clean_unfinished_installations_environment.assert_not_called()
        remove_solution.assert_called_once()

    def test_clean_unfinished_installations_empty(self):

        # mocks
        remove_dc = MagicMock()
        self.album_controller.install_manager()._remove_disc_content_from_solution = (
            remove_dc
        )

        set_cache_paths = MagicMock()
        self.album_controller.collection_manager().solutions().set_cache_paths = (
            set_cache_paths
        )
        get_by_id_mock = MagicMock(
            return_value=self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
        )
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id_mock

        retrieve_and_load_resolve_result = MagicMock()
        self.album_controller.collection_manager().retrieve_and_load_resolve_result = (
            retrieve_and_load_resolve_result
        )

        _clean_unfinished_installations_environment = MagicMock()
        self.install_manager._clean_unfinished_installations_environment = (
            _clean_unfinished_installations_environment
        )

        set_uninstalled = MagicMock()
        self.album_controller.collection_manager().solutions().set_uninstalled = (
            set_uninstalled
        )

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


class TestInstallManagerCollectionParent(TestUnitCoreCommon):
    """Parent detection for solutions built from their collection entry.

    Such solutions carry no "dependencies", their parent is only known from the
    collection index.
    """

    def setUp(self):
        super().setUp()
        self.setup_collection()
        # the real environment manager needs micromamba
        self.album_controller._environment_manager = MagicMock()
        self.environment_manager = self.album_controller.environment_manager()
        self.install_manager: InstallManager = self.album_controller.install_manager()
        self.catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )
        self.parent_entry = CollectionIndex.CollectionSolution(
            {"group": "gp", "name": "np", "version": "vp", "doi": None},  # setup
            {"catalog_id": 1, "parent": None, "children": []},  # internal
        )

    def _mock_clean_unfinished_installations(
        self, unfinished_entry: CollectionIndex.CollectionSolution
    ) -> MagicMock:
        collection_manager = self.album_controller.collection_manager()
        collection_index = collection_manager.get_collection_index()
        collection_index.get_unfinished_installation_solutions = MagicMock(
            return_value=[unfinished_entry]
        )
        collection_manager.catalogs().get_by_id = MagicMock(return_value=self.catalog)
        collection_manager.solutions().set_cache_paths = MagicMock()
        self.install_manager._remove_disc_content_from_solution = MagicMock()
        remove_solution = MagicMock()
        collection_manager.solutions().remove_solution = remove_solution
        return remove_solution

    def test_clean_unfinished_installations_child(self):
        child_entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1"},  # setup
            {"catalog_id": 1, "parent": self.parent_entry},  # internal
        )
        remove_solution = self._mock_clean_unfinished_installations(child_entry)

        # call
        self.install_manager.clean_unfinished_installations()

        # assert - the child runs in the environment of its parent, which stays
        self.environment_manager.set_environment.assert_not_called()
        self.environment_manager.remove_environment.assert_not_called()
        remove_solution.assert_called_once()

    def test_clean_unfinished_installations_no_parent(self):
        entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1"},  # setup
            {"catalog_id": 1, "parent": None},  # internal
        )
        remove_solution = self._mock_clean_unfinished_installations(entry)
        self.environment_manager.set_environment.return_value = "myEnv"

        # call
        self.install_manager.clean_unfinished_installations()

        # assert
        self.environment_manager.set_environment.assert_called_once()
        self.environment_manager.remove_environment.assert_called_once_with("myEnv")
        remove_solution.assert_called_once()

    def test_uninstall_rm_dep_solution_not_loaded(self):
        child_entry = CollectionIndex.CollectionSolution(
            {"group": "g1", "name": "n1", "version": "v1", "doi": None},  # setup
            {"catalog_id": 1, "parent": self.parent_entry, "children": []},  # internal
        )
        resolve_result = ResolveResult(
            path=Path("aPath"),
            catalog=self.catalog,
            collection_entry=child_entry,
            coordinates=Coordinates("g1", "n1", "v1"),
        )

        # mocks
        collection_manager = self.album_controller.collection_manager()
        # the solution file cannot be loaded, the solution is built from its entry
        collection_manager.resolve_installed_and_load = MagicMock(
            side_effect=ValueError
        )
        collection_manager.resolve_installed = MagicMock(return_value=resolve_result)
        get_by_id = MagicMock(return_value=self.catalog)
        collection_manager.catalogs().get_by_id = get_by_id
        self.install_manager._remove_disc_content_from_solution = MagicMock()
        remove_solution = MagicMock()
        collection_manager.solutions().remove_solution = remove_solution

        # the recursive call uninstalling the parent ends up in this mock
        uninstall = self.install_manager.uninstall
        uninstall_parent = MagicMock()
        self.install_manager.uninstall = uninstall_parent

        # call
        uninstall("g1:n1:v1", rm_dep=True)

        # assert
        remove_solution.assert_called_once()
        self.environment_manager.remove_environment.assert_not_called()
        get_by_id.assert_called_once_with(1)
        uninstall_parent.assert_called_once_with(
            "%s:gp:np:vp" % self.catalog.name(), True
        )

    def test_remove_dependencies_parent_declared_in_solution(self):
        # solution loaded from its file: the declared parent is used, as before
        solution = Solution(
            {
                "group": "g1",
                "name": "n1",
                "version": "v1",
                "dependencies": {"parent": {"resolve_solution": "gp:np:vp"}},
            }
        )
        get_by_id = MagicMock()
        self.album_controller.collection_manager().catalogs().get_by_id = get_by_id
        uninstall = MagicMock()
        self.install_manager.uninstall = uninstall

        # call
        self.install_manager._remove_dependencies(solution, True, self.parent_entry)

        # assert
        uninstall.assert_called_once_with("gp:np:vp", True)
        get_by_id.assert_not_called()

    def test_remove_dependencies_no_parent_declared_in_solution(self):
        # solution loaded from its file without parent: nothing to remove, as before
        solution = Solution(
            {
                "group": "g1",
                "name": "n1",
                "version": "v1",
                "dependencies": {"environment_file": "env.yml"},
            }
        )
        uninstall = MagicMock()
        self.install_manager.uninstall = uninstall

        # call
        self.install_manager._remove_dependencies(solution, True, self.parent_entry)

        # assert
        uninstall.assert_not_called()


if __name__ == "__main__":
    unittest.main()
