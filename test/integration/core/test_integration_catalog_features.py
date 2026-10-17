import sys
from pathlib import Path
from test.integration.test_integration_core_common import TestIntegrationCoreCommon
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import ANY, patch

from album.core.model.catalog_updates import ChangeType
from album.core.model.default_values import DefaultValues
from album.core.utils.operations.solution_operations import get_deploy_dict
from album.environments.utils.file_operations import get_dict_from_yml
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
            # the same version for other content
            no_replicability=True,
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
            # deployed again with the same version: for other content
            no_replicability=force_deploy,
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

    def _get_entry(self, catalog, name, version="0.1.0"):
        return (
            self.album_controller.collection_manager()
            .get_collection_index()
            .get_solution_by_catalog_grp_name_version(
                catalog.catalog_id(), Coordinates("group", name, version)
            )
        )

    def _installed_versions(self, catalog, name):
        return sorted(
            entry.setup()["version"]
            for entry in self.album_controller.collection_manager()
            .get_collection_index()
            .get_solutions_by_grp_name("group", name)
            if entry.internal()["catalog_id"] == catalog.catalog_id()
            and entry.internal()["installed"]
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

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_child_and_parent(self, _, __, ___):
        catalog = self._install_child_of_app1()
        # both get a new version, the child runs in the new version of the parent
        self._deploy(catalog, "app1_v2.py")
        self._deploy(catalog, "solution1_app1_v2.py")

        result = self.album_controller.install_manager().upgrade_solutions()

        self.assertEqual(
            [
                "my-catalog:group:app1:0.2.0",
                "my-catalog:group:solution1_app1:0.2.0",
            ],
            result["install"],
        )
        # the child first, the parent once nothing runs in it
        self.assertEqual(
            [
                "my-catalog:group:solution1_app1:0.1.0",
                "my-catalog:group:app1:0.1.0",
            ],
            result["uninstall"],
        )
        for key in ["keep", "unused", "failed"]:
            self.assertEqual([], result[key], key)
        self.assertEqual(["0.2.0"], self._installed_versions(catalog, "app1"))
        self.assertEqual(["0.2.0"], self._installed_versions(catalog, "solution1_app1"))
        child = self._get_entry(catalog, "solution1_app1", "0.2.0")
        self.assertEqual("0.2.0", child.internal()["parent"].setup()["version"])

        # nothing left to do
        result = self.album_controller.install_manager().upgrade_solutions()
        self.assertEqual([], result["install"])
        self.assertEqual([], result["uninstall"])

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_keeps_a_parent_still_used(self, _, __, ___):
        catalog = self._install_child_of_app1()
        # only the parent gets a new version, the child still runs in the old one
        self._deploy(catalog, "app1_v2.py")

        result = self.album_controller.install_manager().upgrade_solutions()

        self.assertEqual(["my-catalog:group:app1:0.2.0"], result["install"])
        self.assertEqual([], result["uninstall"])
        self.assertEqual(
            [
                {
                    "solution": "my-catalog:group:app1:0.1.0",
                    "used_by": ["my-catalog:group:solution1_app1:0.1.0"],
                }
            ],
            result["keep"],
        )
        self.assertEqual(["0.1.0", "0.2.0"], self._installed_versions(catalog, "app1"))
        child = self._get_entry(catalog, "solution1_app1")
        self.assertEqual("0.1.0", child.internal()["parent"].setup()["version"])

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_reports_a_parent_no_longer_used(self, _, __, ___):
        catalog = self._install_child_of_app1()
        # the new version of the child runs in another parent
        self._deploy(catalog, "app2.py")
        self._deploy(catalog, "solution1_app1_v2_on_app2.py")

        result = self.album_controller.install_manager().upgrade_solutions()

        self.assertEqual(
            [
                "my-catalog:group:app2:0.1.0",
                "my-catalog:group:solution1_app1:0.2.0",
            ],
            result["install"],
        )
        self.assertEqual(["my-catalog:group:solution1_app1:0.1.0"], result["uninstall"])
        # the old parent stays, it might be run on its own
        self.assertEqual(["my-catalog:group:app1:0.1.0"], result["unused"])
        self.assertEqual(["0.1.0"], self._installed_versions(catalog, "app1"))

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_dry_run(self, _, __, ___):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app1_v2.py")
        self._deploy(catalog, "solution1_app1_v2.py")

        result = self.album_controller.install_manager().upgrade_solutions(dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(
            [
                "my-catalog:group:app1:0.2.0",
                "my-catalog:group:solution1_app1:0.2.0",
            ],
            result["install"],
        )
        self.assertEqual(
            [
                "my-catalog:group:solution1_app1:0.1.0",
                "my-catalog:group:app1:0.1.0",
            ],
            result["uninstall"],
        )
        # nothing changed, the new versions are not even in the collection
        self.assertEqual(["0.1.0"], self._installed_versions(catalog, "app1"))
        self.assertEqual(["0.1.0"], self._installed_versions(catalog, "solution1_app1"))
        self.assertIsNone(self._get_entry(catalog, "app1", "0.2.0"))

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_keeps_a_version_used_meanwhile(self, _, __, ___):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app1_v2.py")
        install_manager = self.album_controller.install_manager()
        runs_in = install_manager._runs_in
        decided = []

        def decided_before_the_child_was_installed(entry, removed):
            if not decided:
                decided.append(entry)
                return []
            return runs_in(entry, removed)

        install_manager._runs_in = decided_before_the_child_was_installed

        result = install_manager.upgrade_solutions()

        # kept, not failed
        self.assertEqual([], result["failed"])
        self.assertEqual([], result["uninstall"])
        self.assertEqual(
            [
                {
                    "solution": "my-catalog:group:app1:0.1.0",
                    "used_by": ["my-catalog:group:solution1_app1:0.1.0"],
                }
            ],
            result["keep"],
        )
        self.assertEqual(["0.1.0", "0.2.0"], self._installed_versions(catalog, "app1"))

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_ignores_a_version_uninstalled_meanwhile(
        self, _, __, ___
    ):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app1_v2.py")
        self._deploy(catalog, "solution1_app1_v2.py")
        install_manager = self.album_controller.install_manager()
        lock_and_uninstall = install_manager._lock_and_uninstall

        def uninstalled_by_another_process(solution, rm_dep, as_dependency):
            lock_and_uninstall(solution, rm_dep, as_dependency)
            raise ValueError('Solution "%s" is not installed.' % solution)

        install_manager._lock_and_uninstall = uninstalled_by_another_process

        result = install_manager.upgrade_solutions()

        # neither reported as uninstalled by this process nor as failed
        self.assertEqual([], result["failed"])
        self.assertEqual([], result["uninstall"])
        self.assertEqual(["0.2.0"], self._installed_versions(catalog, "app1"))
        self.assertEqual(["0.2.0"], self._installed_versions(catalog, "solution1_app1"))

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_given_solution(self, _, __, ___):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app1_v2.py")
        self._deploy(catalog, "solution1_app1_v2.py")

        result = self.album_controller.install_manager().upgrade_solutions(
            ["group:app1"]
        )

        # only the parent is upgraded, the child still runs in its old version
        self.assertEqual(["my-catalog:group:app1:0.2.0"], result["install"])
        self.assertEqual([], result["uninstall"])
        self.assertEqual(
            ["my-catalog:group:app1:0.1.0"],
            [kept["solution"] for kept in result["keep"]],
        )
        self.assertEqual(["0.1.0"], self._installed_versions(catalog, "solution1_app1"))

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_upgrade_solutions_keeps_the_old_version_if_the_new_one_fails(
        self, _, install_environment, __
    ):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app1_v2.py")
        self._deploy(catalog, "solution1_app1_v2.py")

        def fail_for_new_versions(solution, *args):
            if solution.coordinates().version() == "0.2.0":
                raise RuntimeError("Cannot create the environment!")

        install_environment.side_effect = fail_for_new_versions

        result = self.album_controller.install_manager().upgrade_solutions()

        self.assertEqual(
            [
                "my-catalog:group:app1:0.2.0",
                "my-catalog:group:solution1_app1:0.2.0",
            ],
            [failure["solution"] for failure in result["failed"]],
        )
        self.assertEqual([], result["install"])
        self.assertEqual([], result["uninstall"])
        self.assertEqual(["0.1.0"], self._installed_versions(catalog, "app1"))
        self.assertEqual(["0.1.0"], self._installed_versions(catalog, "solution1_app1"))

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_a_parent_deployed_again(
        self, _, install_environment, remove_environment
    ):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "app1_changed.py", force_deploy=True)
        self._update_and_upgrade(catalog)
        self.assertIn(
            'Solution "group:app1:0.1.0" changed in catalog "my-catalog" after it was '
            'installed. "album install --reinstall my-catalog:group:app1:0.1.0" '
            "installs it again.",
            self.get_logs_as_string(),
        )
        install_environment.reset_mock()
        install_manager = self.album_controller.install_manager()

        # its child keeps it: the child might not work in its new environment
        with self.assertRaises(RuntimeError) as e:
            install_manager.install("my-catalog:group:app1:0.1.0", reinstall=True)
        self.assertEqual(
            'Cannot install "my-catalog:group:app1:0.1.0" again, nothing was changed: '
            '"my-catalog:group:solution1_app1:0.1.0" runs in its environment, and might '
            "not work in its new one. Uninstall it first, and install it again "
            "afterwards.",
            str(e.exception),
        )
        remove_environment.assert_not_called()
        self.assertTrue(
            self._get_entry(catalog, "solution1_app1").internal()["installed"]
        )

        # by hand, as the message says
        install_manager.uninstall("my-catalog:group:solution1_app1:0.1.0")
        install_manager.install(
            "my-catalog:group:app1:0.1.0", reinstall=True, no_conda_lock=True
        )
        install_manager.install("my-catalog:group:solution1_app1:0.1.0")

        # its environment is built again, without its lock file as asked, and the child
        # installed into it again
        remove_environment.assert_called_once()
        install_environment.assert_called_once_with(ANY, False, True)
        child = self._get_entry(catalog, "solution1_app1")
        self.assertTrue(child.internal()["installed"])
        self.assertEqual("app1", child.internal()["parent"].setup()["name"])
        solution_file = self.album_controller.solutions().get_solution_file(
            catalog, Coordinates("group", "app1", "0.1.0")
        )
        self.assertIn(
            "deployed again with the same version",
            Path(solution_file).read_text(encoding="utf-8"),
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_from_a_file(self, _, install_environment, __):
        install_manager = self.album_controller.install_manager()
        path = self.get_test_solution_path("app1.py")
        cache_catalog = self.album_controller.catalogs().get_cache_catalog()
        app1 = Coordinates("group", "app1", "0.1.0")

        # not installed: installed as usual
        install_manager.install(path, reinstall=True)
        self.assertTrue(
            self.album_controller.solutions().is_installed(cache_catalog, app1)
        )

        # given by its coordinates, it is installed again from its copy in album
        install_manager.install("group:app1:0.1.0", reinstall=True)
        self.assertTrue(
            self.album_controller.solutions().is_installed(cache_catalog, app1)
        )

        # given by its file, from the file
        install_manager.install(path, reinstall=True)
        self.assertTrue(
            self.album_controller.solutions().is_installed(cache_catalog, app1)
        )
        self.assertEqual(3, install_environment.call_count)

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_a_parent_with_a_child_from_a_file(
        self, _, __, remove_environment
    ):
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        self._deploy(catalog, "app1.py")
        self._update_and_upgrade(catalog)
        install_manager = self.album_controller.install_manager()
        # the child from a file, its parent from the catalog
        install_manager.install(self.get_test_solution_path("solution1_app1.py"))
        cache_catalog = self.album_controller.catalogs().get_cache_catalog()
        child = Coordinates("group", "solution1_app1", "0.1.0")

        # installing the environment of the parent again could break the child
        with self.assertRaises(RuntimeError) as e:
            install_manager.install("my-catalog:group:app1:0.1.0", reinstall=True)

        self.assertEqual(
            'Cannot install "my-catalog:group:app1:0.1.0" again, nothing was changed: '
            '"cache_catalog:group:solution1_app1:0.1.0" runs in its environment, and '
            "might not work in its new one. Uninstall it first, and install it again "
            "afterwards.",
            str(e.exception),
        )
        # nothing changed
        remove_environment.assert_not_called()
        self.assertTrue(
            self.album_controller.solutions().is_installed(cache_catalog, child)
        )
        self.assertTrue(self._get_entry(catalog, "app1").internal()["installed"])

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_downloads_before_uninstalling(
        self, _, __, remove_environment
    ):
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        self._deploy(catalog, "app1.py")
        self._update_and_upgrade(catalog)
        self.album_controller.install_manager().install("my-catalog:group:app1:0.1.0")

        with patch(
            "album.core.controller.collection.solution_handler.SolutionHandler.retrieve_solution",
            side_effect=ConnectionError("offline"),
        ):
            with self.assertRaises(RuntimeError) as e:
                self.album_controller.install_manager().install(
                    "my-catalog:group:app1:0.1.0", reinstall=True
                )

        self.assertIn("nothing was changed: offline", str(e.exception))
        remove_environment.assert_not_called()
        self.assertTrue(self._get_entry(catalog, "app1").internal()["installed"])

    def _deploy_changed(self, catalog, solution_file, old, new):
        """Deploy a test solution again with the same version, with old replaced by new."""
        path = Path(self.tmp_dir.name).joinpath(solution_file)
        content = Path(self.get_test_solution_path(solution_file)).read_text("utf-8")
        self.assertIn(old, content)
        path.write_text(content.replace(old, new), encoding="utf-8")
        self._deploy(catalog, str(path), force_deploy=True)
        self._update_and_upgrade(catalog)

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_parent_not_found(self, _, __, remove_environment):
        catalog = self._install_child_of_app1()
        self._deploy_changed(
            catalog, "solution1_app1.py", '"name": "app1"', '"name": "app_gone"'
        )

        with self.assertRaises(RuntimeError) as e:
            self.album_controller.install_manager().install(
                "my-catalog:group:solution1_app1:0.1.0", reinstall=True
            )

        self.assertEqual(
            'Cannot install "my-catalog:group:solution1_app1:0.1.0" again, nothing was '
            'changed: its parent "group:app_gone:0.1.0" is not found.',
            str(e.exception),
        )
        remove_environment.assert_not_called()
        self.assertTrue(
            self._get_entry(catalog, "solution1_app1").internal()["installed"]
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_parent_with_another_api_version(
        self, _, __, remove_environment
    ):
        catalog = self._install_child_of_app1()
        self._deploy_changed(
            catalog,
            "solution1_app1.py",
            'album_api_version="0.7.1"',
            'album_api_version="0.7.2"',
        )

        with self.assertRaises(RuntimeError) as e:
            self.album_controller.install_manager().install(
                "my-catalog:group:solution1_app1:0.1.0", reinstall=True
            )

        self.assertEqual(
            'Cannot install "my-catalog:group:solution1_app1:0.1.0" again, nothing was '
            'changed: its parent "group:app1:0.1.0" has API version 0.7.1, not 0.7.2.',
            str(e.exception),
        )
        remove_environment.assert_not_called()
        self.assertTrue(
            self._get_entry(catalog, "solution1_app1").internal()["installed"]
        )

    def test_deploy_no_replicability(self):
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        folder = Path(self.tmp_dir.name).joinpath("unpinned")
        folder.mkdir()
        folder.joinpath("solution.py").write_text(
            "from album.runner.api import setup\n\n"
            "resources = '''resources:\n  data:\n    name: data.csv\n"
            "    url: https://example.org/data.csv\n'''\n\n"
            'setup(group="group", name="unpinned", version="0.1.0", '
            'album_api_version="0.7.1", dependencies={"resource_file": resources})\n',
            encoding="utf-8",
        )

        def deploy(no_replicability):
            self.album_controller.deploy_manager().deploy(
                str(folder),
                catalog_name=catalog.name(),
                changelog="deploy",
                dry_run=False,
                git_email=DefaultValues.catalog_git_email.value,
                git_name=DefaultValues.catalog_git_user.value,
                no_conda_lock=True,
                no_replicability=no_replicability,
            )

        # a resource from a url without a hash: refused
        with self.assertRaises(RuntimeError) as e:
            deploy(no_replicability=False)
        url_reason = (
            'resource "data" is downloaded from https://example.org/data.csv without a '
            "hash, its content can change"
        )
        self.assertIn(url_reason, str(e.exception))

        # deployed with the flag, the reasons stored with the solution
        deploy(no_replicability=True)
        solution_yml = (
            self.album_controller.deploy_manager()
            .get_download_path(catalog)
            .joinpath(
                self.configuration.get_solution_path_suffix_unversioned(
                    Coordinates("group", "unpinned", "0.1.0")
                ),
                "solution.yml",
            )
        )
        self.assertEqual(
            {
                "reasons": [
                    url_reason,
                    "it is deployed without a lock file (--no-conda-lock), its "
                    "environment is solved again when it is installed",
                ]
            },
            get_dict_from_yml(solution_yml)["replicability"],
        )

    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    @patch(
        "album.environments.environment_api.EnvironmentAPI.create_environment_prefer_lock_file"
    )
    def test_install_shows_replicability_reasons(self, _, __):
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        # deployed without a lock file
        self._deploy(catalog, "app1.py")
        self._update_and_upgrade(catalog)

        self.album_controller.install_manager().install("my-catalog:group:app1:0.1.0")

        # the reason album deploy stored, not a second warning of its own
        logs = self.get_logs_as_string()
        self.assertIn(
            'Not technically replicable, "group:app1:0.1.0": it is deployed without a '
            "lock file (--no-conda-lock), its environment is solved again when it is "
            "installed",
            logs,
        )
        self.assertNotIn("it has no lock file", logs)

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_parent_from_another_catalog(self, _, __):
        catalogs = self.album_controller.collection_manager().catalogs()
        parents_src, _ = self.setup_empty_catalog("parents")
        parents = catalogs.add_by_src(parents_src)
        children_src, _ = self.setup_empty_catalog("children")
        children = catalogs.add_by_src(children_src)
        self._deploy(parents, "app1.py")
        self._deploy(children, "solution1_app1.py")
        self._update_and_upgrade(parents)
        self._update_and_upgrade(children)

        self.album_controller.install_manager().install(
            "children:group:solution1_app1:0.1.0"
        )

        # not in the catalog of the solution: taken from the other one, with a warning
        self.assertTrue(self._get_entry(parents, "app1").internal()["installed"])
        self.assertIn(
            'Not technically replicable, "group:solution1_app1:0.1.0": its parent '
            '"group:app1:0.1.0" is not in its catalog "children", album takes the one '
            "it finds first.",
            self.get_logs_as_string(),
        )

    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    @patch(
        "album.environments.environment_api.EnvironmentAPI.create_environment_prefer_lock_file"
    )
    def test_install_deployed_solution_environment_file_outside_solution_folder(
        self, create_environment, _
    ):
        catalog_src, _ = self.setup_empty_catalog("my-catalog")
        catalog = (
            self.album_controller.collection_manager()
            .catalogs()
            .add_by_src(catalog_src)
        )
        environment_file = Path(self.tmp_dir.name).joinpath("shared", "environment.yml")
        environment_file.parent.mkdir()
        environment_file.write_text(
            "channels:\n  - conda-forge\ndependencies:\n  - python=3.12\n",
            encoding="utf-8",
        )
        folder = Path(self.tmp_dir.name).joinpath("my-solution")
        folder.mkdir()
        folder.joinpath("solution.py").write_text(
            "from album.runner.api import setup\n\n"
            'setup(group="group", name="shared_env", version="0.1.0", '
            'album_api_version="0.7.1", '
            "dependencies={'environment_file': %r})\n" % str(environment_file),
            encoding="utf-8",
        )
        self.album_controller.deploy_manager().deploy(
            str(folder),
            catalog_name=catalog.name(),
            changelog="deploy",
            dry_run=False,
            git_email=DefaultValues.catalog_git_email.value,
            git_name=DefaultValues.catalog_git_user.value,
            no_conda_lock=True,
        )
        self._update_and_upgrade(catalog)

        # installed where the environment file is not
        environment_file.unlink()
        self.album_controller.install_manager().install(
            "my-catalog:group:shared_env:0.1.0"
        )

        # from the environment album deploy wrote
        environment = get_dict_from_yml(create_environment.call_args[0][0].yaml_file())
        self.assertIn("python=3.12", environment["dependencies"])
        self.assertIn(
            "conda-forge::%s=0.7.1" % DefaultValues.runner_api_package_name.value,
            environment["dependencies"],
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_checks_files_before_uninstalling(
        self, _, __, remove_environment
    ):
        folder = Path(self.tmp_dir.name).joinpath("legacy")
        folder.mkdir()
        folder.joinpath("environment.yml").write_text(
            "channels:\n  - conda-forge\ndependencies:\n  - python\n", encoding="utf-8"
        )
        folder.joinpath("solution.py").write_text(
            "from album.runner.api import setup\n\n"
            'setup(group="group", name="legacy", version="0.1.0", '
            'album_api_version="0.7.1", '
            'dependencies={"environment_file": "environment.yml"})\n',
            encoding="utf-8",
        )
        install_manager = self.album_controller.install_manager()
        install_manager.install(str(folder))
        cache_catalog = self.album_controller.catalogs().get_cache_catalog()
        legacy = Coordinates("group", "legacy", "0.1.0")
        name = f"{cache_catalog.name()}:group:legacy:0.1.0"

        # its environment file, outside the folder of the solution, is gone meanwhile
        outside = Path(self.tmp_dir.name).joinpath("environment.yml")
        installed_copy = self.album_controller.solutions().get_solution_file(
            cache_catalog, legacy
        )
        installed_copy.write_text(
            installed_copy.read_text(encoding="utf-8").replace(
                '"environment.yml"', repr(str(outside))
            ),
            encoding="utf-8",
        )

        with self.assertRaises(RuntimeError) as e:
            install_manager.install("group:legacy:0.1.0", reinstall=True)

        self.assertEqual(
            f'Cannot install "{name}" again, nothing was changed: environment_file '
            f'"{outside}" does not exist. Uninstall "{name}" and install it by hand.',
            str(e.exception),
        )
        remove_environment.assert_not_called()
        self.assertTrue(
            self.album_controller.solutions().is_installed(cache_catalog, legacy)
        )

    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.remove_environment"
    )
    @patch(
        "album.core.controller.environment_manager.EnvironmentManager.install_environment"
    )
    @patch("album.core.controller.script_manager.ScriptManager.run_solution_script")
    def test_install_reinstall_a_solution_others_run_in(
        self, _, __, remove_environment
    ):
        catalog = self._install_child_of_app1()
        self._deploy(catalog, "solution2_app1.py")
        self._update_and_upgrade(catalog)
        install_manager = self.album_controller.install_manager()
        install_manager.install("my-catalog:group:solution2_app1:0.1.0")

        with self.assertRaises(RuntimeError) as e:
            install_manager.install("my-catalog:group:app1:0.1.0", reinstall=True)

        self.assertEqual(
            'Cannot install "my-catalog:group:app1:0.1.0" again, nothing was changed: '
            '"my-catalog:group:solution1_app1:0.1.0", '
            '"my-catalog:group:solution2_app1:0.1.0" run in its environment, and might '
            "not work in its new one. Uninstall them first, and install them again "
            "afterwards.",
            str(e.exception),
        )
        remove_environment.assert_not_called()
        for name in ["app1", "solution1_app1", "solution2_app1"]:
            self.assertTrue(self._get_entry(catalog, name).internal()["installed"])
