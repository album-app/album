import sys
from pathlib import Path
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import patch

from album.core.model.catalog_updates import ChangeType
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.runner.core.model.coordinates import Coordinates
from album.runner.core.model.solution import Solution


class TestIntegrationCatalogFeatures(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()
        self.configuration = self.album_controller.configuration()

    def tearDown(self) -> None:
        super().tearDown()

    def add_solutions(self, catalog, solutions):
        with catalog.retrieve_catalog(
            Path(self.tmp_dir.name).joinpath("tmp_repo")
        ) as tmp_repo:
            tmp_repo.config_writer().set_value("user", "email", "myEmail").release()
            tmp_repo.config_writer().set_value("user", "name", "myName").release()
            catalog.set_index_path(
                Path(tmp_repo.working_tree_dir).joinpath(
                    DefaultValues.catalog_index_file_name.value
                )
            )
            catalog.load_index()
            for s in solutions:
                len_before = len(catalog.index().get_all_solutions())
                catalog.add(s)
                self.assertEqual(
                    len_before + 1, len(catalog.index().get_all_solutions())
                )

            tmp_repo.git.add(DefaultValues.catalog_index_file_name.value)
            tmp_repo.git.commit(m="commit_message")
            tmp_repo.git.push()

    def test_add_remove_catalog(self):
        # prepare
        self.assertIsNotNone(self.configuration)
        initial_catalogs = self.configuration.get_initial_catalogs().copy()

        self.assertIsNotNone(initial_catalogs)
        initial_len = 1  # the cache catalog always configured

        new_catalog_src, _ = self.setup_empty_catalog("catalog_integration_test")

        modified_catalog_src = new_catalog_src.joinpath(
            "..", "catalog_integration_test"
        )

        # call
        self.album_controller.collection_manager().catalogs().add_by_src(
            modified_catalog_src
        )

        # assert
        self.assertNotIn("ERROR", self.get_logs_as_string())
        catalogs = (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_all_catalogs()
        )
        catalog_cache_path_to_be_deleted = catalogs[-1]["path"]
        self.assertEqual(initial_len + 1, len(catalogs))
        self.assertEqual(
            str(new_catalog_src.resolve()), catalogs[len(catalogs) - 1]["src"]
        )

        # deploy in catalog
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("solution11_minimal.py")),
            catalog_name="catalog_integration_test",
            changelog="something changed",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
            no_conda_lock=True,
        )

        catalog_download_path = self.configuration.cache_path_download().joinpath(
            "catalog_integration_test"
        )
        self.assertTrue(catalog_download_path.exists())

        # gather arguments remove
        sys.argv = ["", "remove-catalog", new_catalog_src]

        # call
        self.album_controller.collection_manager().catalogs().remove_from_collection_by_src(
            new_catalog_src
        )

        # assert
        self.assertNotIn("ERROR", self.get_logs_as_string())
        catalogs = (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_all_catalogs()
        )
        self.assertEqual(initial_len, len(catalogs))
        for catalog in catalogs:
            if catalog["name"] == "cache_catalog":
                self.assertIsNone(initial_catalogs.get(catalog["name"]))
            else:
                self.assertIsNotNone(initial_catalogs.get(catalog["name"]))
        self.assertFalse(
            Path(catalog_cache_path_to_be_deleted).exists()
        )  # cache path deleted
        self.assertFalse(catalog_download_path.exists())  # download path got deleted
        self.assertTrue(new_catalog_src.exists())  # src path still available!

    def test_update_collection(self):
        # create a catalog and its meta file and DB file in a src
        catalog_src, _ = self.setup_empty_catalog("my-catalog")

        # add catalog
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        self.assertTrue(catalog.is_local())

        # create two solutions
        solution_dict = TestUnitCoreCommon.get_solution_dict()
        solution = Solution(solution_dict)
        solution2_dict = solution_dict.copy()
        solution2_dict["name"] = "something else"
        solution2 = Solution(solution2_dict)

        # check that initially no updates are available
        dif = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection(catalog.name(), dry_run=True)
        )

        self.assertIsNotNone(dif)
        self.assertEqual(1, len(dif.keys()))
        self.assertIsNotNone(dif[catalog.name()])
        self.assertIsNotNone(dif[catalog.name()].catalog_attribute_changes())
        self.assertIsNotNone(dif[catalog.name()].solution_changes())
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(0, len(dif[catalog.name()].solution_changes()))

        # add new solution to catalog
        self.add_solutions(catalog, [solution, solution2])

        dif = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection(catalog.name(), dry_run=True)
        )

        self.assertEqual(1, len(dif.keys()))
        self.assertIsNotNone(dif[catalog.name()])
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(2, len(dif[catalog.name()].solution_changes()))
        self.assertEqual(
            ChangeType.ADDED, dif[catalog.name()].solution_changes()[0].change_type()
        )

        # update collection
        dif = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection(catalog.name(), dry_run=False)
        )

        self.assertIsNotNone(dif[catalog.name()])
        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(2, len(dif[catalog.name()].solution_changes()))
        self.assertEqual(
            ChangeType.ADDED, dif[catalog.name()].solution_changes()[0].change_type()
        )

        dif = (
            self.album_controller.collection_manager()
            .catalogs()
            .update_collection(catalog.name(), dry_run=True)
        )

        self.assertEqual(0, len(dif[catalog.name()].catalog_attribute_changes()))
        self.assertEqual(0, len(dif[catalog.name()].solution_changes()))

    def test_update_upgrade(self):
        initial_len = len(
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_all_catalogs()
        )  # has the default catalogs

        # add catalog
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )  # its emtpy

        # assert it got added
        self.assertEqual(
            initial_len + 1,
            len(
                self.album_controller.collection_manager()
                .get_collection_index()
                .get_all_catalogs()
            ),
        )
        self.assertTrue(catalog.is_local())

        # check its empty
        self.assertEqual(0, len(catalog.index().get_all_solutions()))

        # add new solution to catalog  - not yet in the collection
        solution_dict = TestUnitCoreCommon.get_solution_dict()
        solution_dict["name"] = "myAwesomeSolution"
        solution = Solution(solution_dict)

        self.add_solutions(catalog, [solution])

        # update collection
        self.album_controller.collection_manager().catalogs().update_any()

        self.assertNotIn("ERROR", self.get_logs_as_string())

        # upgrade collection
        self.album_controller.collection_manager().catalogs().update_collection()

        self.assertNotIn("ERROR", self.get_logs_as_string())

        # assert
        solutions = (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solutions_by_catalog(catalog.catalog_id())
        )
        self.assertEqual(1, len(solutions))

        # compare solution in collection to original solution
        solution_in_collection = solutions[0]

        sol = {}
        solution_in_col = {}
        for key in get_deploy_dict(solution).keys():
            if key == "timestamp":
                continue
            sol[key] = solution.setup()[key]
            solution_in_col[key] = solution_in_collection.setup()[key]

        self.assertEqual(sol, solution_in_col)

        catalog.dispose()

    @patch(
        "album.environments.controller.conda_lock_manager.CondaLockManager.create_conda_lock_file"
    )
    def test_update_upgrade_override(self, conda_lock_mock):
        conda_lock_mock.return_value = None
        initial_len = len(
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_all_catalogs()
        )  # has the default catalogs

        # add catalog
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )  # its emtpy

        # assert it got added
        self.assertEqual(
            initial_len + 1,
            len(
                self.album_controller.collection_manager()
                .get_collection_index()
                .get_all_catalogs()
            ),
        )

        # check its empty
        self.assertEqual(0, len(catalog.index().get_all_solutions()))

        # deploy to parent to catalog
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("app1.py")),
            catalog_name=catalog.name(),
            changelog="initial deploy",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # deploy to solution to catalog
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("solution1_app1.py")),
            catalog_name=catalog.name(),
            changelog="initial deploy",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # update
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        # upgrade
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name()
        )

        # check both are deployed
        self.assertEqual(2, len(catalog.index().get_all_solutions()))

        # install
        coordinates = Coordinates("group", "solution1_app1", "0.1.0")
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")

        # check file is copied
        local_file = (
            self.album_controller.collection_manager()
            .solutions()
            .get_solution_file(catalog, coordinates)
        )
        self.assertTrue(local_file.exists())
        copy_date = local_file.stat().st_mtime

        # make a re-deploy with changed solution code but same coordinates
        self.album_controller.deploy_manager().deploy(
            str(self.get_test_solution_path("solution1_app1_changed_parent.py")),
            catalog_name=catalog.name(),
            changelog="something changed... in the neighborhood... who you gonna call?",
            dry_run=False,
            force_deploy=True,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

        # update
        self.album_controller.collection_manager().catalogs().update_any(catalog.name())
        # upgrade
        self.album_controller.collection_manager().catalogs().update_collection(
            catalog.name(), override=True
        )

        # assert copy_date unequal due to renewed download of solution file
        self.assertNotEqual(copy_date, local_file.stat().st_mtime)

        # assert parent did NOT CHANGE! (we are aware that this leave behind broken installations!)
        parent = (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(catalog.catalog_id(), coordinates)
            .internal()["parent"]
        )
        self.assertEqual("app1", parent.setup()["name"])

    def _deploy(self, catalog, solution_file, force_deploy=False):
        self.album_controller.deploy_manager().deploy(
            self.get_test_solution_path(solution_file),
            catalog_name=catalog.name(),
            changelog="deploy",
            dry_run=False,
            force_deploy=force_deploy,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
            no_conda_lock=True,
        )

    def _undeploy(self, catalog, solution):
        self.album_controller.deploy_manager().undeploy(
            solution,
            catalog_name=catalog.name(),
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
        )

    def _update_and_upgrade(self, catalog, override=False):
        catalogs = self.album_controller.collection_manager().catalogs()
        catalogs.update_any(catalog.name())
        return catalogs.update_collection(catalog.name(), override=override)[
            catalog.name()
        ]

    def _get_entry(self, catalog, name):
        return (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                catalog.catalog_id(), Coordinates("group", name, "0.1.0")
            )
        )

    def _install_child_of_app1(self):
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        self._deploy(catalog, "app1.py")
        self._deploy(catalog, "solution1_app1.py")
        self._update_and_upgrade(catalog)
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")
        return catalog

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_changed_parent_keeps_its_children(self, _, __, remove_environment):
        catalog = self._install_child_of_app1()
        parent_id = self._get_entry(catalog, "app1").internal()["collection_id"]

        # the parent is deployed again with the same version
        self._deploy(catalog, "app1_changed.py", force_deploy=True)
        updates = self._update_and_upgrade(catalog)
        self.assertEqual(
            [(Coordinates("group", "app1", "0.1.0"), ChangeType.CHANGED)],
            [(c.coordinates(), c.change_type()) for c in updates.solution_changes()],
        )

        parent = self._get_entry(catalog, "app1")
        self.assertEqual(
            "app one, deployed again with the same version", parent.setup()["title"]
        )
        self.assertEqual(parent_id, parent.internal()["collection_id"])
        self.assertTrue(parent.internal()["installed"])

        # the child still runs in the environment of the parent
        child = self._get_entry(catalog, "solution1_app1")
        self.assertEqual(
            parent_id, child.internal()["parent"].internal()["collection_id"]
        )
        environment = self.album_controller.environment_manager().set_environment(
            self.album_controller.collection_manager().resolve_installed_and_load(
                "group:solution1_app1:0.1.0"
            )
        )
        self.assertEqual(
            self.album_controller.environment_manager().get_environment_name(
                Coordinates("group", "app1", "0.1.0"), catalog
            ),
            environment.name(),
        )

        # and the parent cannot be uninstalled before the child
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().uninstall("group:app1:0.1.0")
        remove_environment.assert_not_called()

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_keeps_installed_solutions_removed_from_the_catalog(
        self, _, __, remove_environment
    ):
        catalog = self._install_child_of_app1()

        self._undeploy(catalog, "group:solution1_app1:0.1.0")
        self._undeploy(catalog, "group:app1:0.1.0")
        updates = self._update_and_upgrade(catalog)
        self.assertEqual(
            [ChangeType.REMOVED, ChangeType.REMOVED],
            [c.change_type() for c in updates.solution_changes()],
        )
        self.assertIn(
            'Solution "group:app1:0.1.0" was removed from catalog "my-catalog", '
            "but it is installed. It stays in your collection until you uninstall it.",
            self.get_logs_as_string(),
        )

        # both stay installed, the child in the environment of the parent
        parent = self._get_entry(catalog, "app1")
        child = self._get_entry(catalog, "solution1_app1")
        self.assertTrue(parent.internal()["installed"])
        self.assertTrue(child.internal()["installed"])
        self.assertEqual(
            parent.internal()["collection_id"],
            child.internal()["parent"].internal()["collection_id"],
        )

        # they are uninstalled like any other solution, the child first
        with self.assertRaises(RuntimeError):
            self.album_controller.install_manager().uninstall("group:app1:0.1.0")
        self.album_controller.install_manager().uninstall("group:solution1_app1:0.1.0")
        self.album_controller.install_manager().uninstall("group:app1:0.1.0")
        remove_environment.assert_called_once()

        # the next upgrade removes them from the collection
        self._update_and_upgrade(catalog)
        self.assertIsNone(self._get_entry(catalog, "app1"))
        self.assertIsNone(self._get_entry(catalog, "solution1_app1"))
        self.assertTrue(
            self.album_controller.collection_manager()
            .get_collection_index()
            .is_table_empty("collection_collection")
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_again_after_upgrade_override_changed_the_parent(self, _, __, ___):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app2.py")

        # the child is deployed again with the same version, but another parent
        self._deploy(catalog, "solution1_app1_changed_parent.py", force_deploy=True)
        self._update_and_upgrade(catalog, override=True)
        child = self._get_entry(catalog, "solution1_app1")
        self.assertEqual("app1", child.internal()["parent"].setup()["name"])

        # installed again, it runs in the environment of its new parent
        self.album_controller.install_manager().uninstall("group:solution1_app1:0.1.0")
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")
        child = self._get_entry(catalog, "solution1_app1")
        self.assertEqual("app2", child.internal()["parent"].setup()["name"])

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_again_a_solution_that_lost_its_parent(self, _, __, ___):
        catalog = self._install_child_of_app1()
        # older album versions left the link pointing to a parent entry they had replaced
        index = self.album_controller.collection_manager().get_collection_index()
        index.get_cursor().execute(
            "UPDATE collection_collection SET collection_id_parent = 99"
        )
        index.close_current_connection()
        self.assertIsNone(
            self._get_entry(catalog, "solution1_app1").internal()["parent"]
        )

        self.album_controller.install_manager().uninstall("group:solution1_app1:0.1.0")
        self.album_controller.install_manager().install("group:solution1_app1:0.1.0")
        child = self._get_entry(catalog, "solution1_app1")
        self.assertEqual("app1", child.internal()["parent"].setup()["name"])

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.get_environment_path"
    )
    def test_resolve(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_environment_handler()
            .get_package_manager()
            .get_active_environment_path()
        )
        self.fake_install(
            self.get_test_solution_path("solution11_minimal.py"),
            create_environment=False,
        )

        res = self.album_controller.collection_manager()._search(
            "cache_catalog:group:name:0.1.0"
        )
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.1.0", res.setup()["version"])
        res = self.album_controller.collection_manager()._search("group:name:0.1.0")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.1.0", res.setup()["version"])
        res = self.album_controller.collection_manager()._search("name")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.1.0", res.setup()["version"])
        res = self.album_controller.collection_manager()._search("name:0.1.0")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.1.0", res.setup()["version"])
        res = self.album_controller.collection_manager()._search("group:name")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.1.0", res.setup()["version"])

        self.fake_install(
            self.get_test_solution_path("solution11_changed_version.py"),
            create_environment=False,
        )

        res = self.album_controller.collection_manager()._search("name")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.2.0", res.setup()["version"])

        res = self.album_controller.collection_manager()._search("group:name")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.2.0", res.setup()["version"])

        res = self.album_controller.collection_manager()._search("name:0.1.0")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.1.0", res.setup()["version"])

        self.fake_install(
            self.get_test_solution_path("solution11_changed_group.py"),
            create_environment=False,
        )

        res = self.album_controller.collection_manager()._search("name:0.2.0")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.2.0", res.setup()["version"])

        res = self.album_controller.collection_manager()._search("group:name:0.2.0")
        self.assertIsNotNone(res)
        self.assertEqual("group", res.setup()["group"])
        self.assertEqual("name", res.setup()["name"])
        self.assertEqual("0.2.0", res.setup()["version"])

        with self.assertRaises(LookupError) as e:
            self.album_controller.collection_manager()._resolve("ame")
        self.assertIn(
            "Cannot find solution ame! Try <doi>:<prefix>/<suffix> or <prefix>/<suffix> "
            "or <group>:<name>:<version> or <catalog>:<group>:<name>:<version> "
            "or point to a valid file or folder! Aborting...",
            str(e.exception),
        )
