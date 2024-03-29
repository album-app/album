import os
from pathlib import Path
from typing import Optional

from album.core.model.default_values import DefaultValues
from album.core.model.environment import Environment
from album.core.utils.operations.file_operations import copy
from album.runner.core.model.solution import Solution
from test.test_common import TestCommon


class TestIntegrationCoreCommon(TestCommon):
    def setUp(self):
        super().setUp()
        self.setup_album_controller()
        self.setup_collection()

    def tearDown(self) -> None:
        self._remove_test_environments()
        super().tearDown()

    def _remove_test_environments(self):
        local_catalog_name = str(
            self.album_controller.collection_manager()
            .catalogs()
            .get_cache_catalog()
            .name()
        )
        env_names = [
            local_catalog_name + "_group_name_0.1.0",
            local_catalog_name + "_group_app1_0.1.0",
            local_catalog_name + "_group_app2_0.1.0",
            local_catalog_name + "_group_solution1_app1_0.1.0",
            local_catalog_name + "_group_solution2_app1_0.1.0",
            local_catalog_name + "_group_solution3_noparent_0.1.0",
            local_catalog_name + "_group_solution4_app2_0.1.0",
            local_catalog_name + "_group_solution5_app2_0.1.0",
            local_catalog_name + "_group_solution6_noparent_test_0.1.0",
            local_catalog_name + "_group_solution7_long_routines_0.1.0",
            local_catalog_name + "_group_solution8_arguments_0.1.0",
            local_catalog_name + "_group_solution9_throws_exception_0.1.0",
            local_catalog_name + "_group_solution10_uninstall_0.1.0",
            local_catalog_name + "_group_solution13_faultySolution_0.1.0",
            local_catalog_name + "_group_solution_with_steps_0.1.0",
            local_catalog_name + "_solution_with_steps_grouped_0.1.0",
        ]
        for e in env_names:
            if (
                self.album_controller.environment_manager()
                .get_package_manager()
                .environment_exists(e)
            ):
                self.album_controller.environment_manager().get_package_manager().remove_environment(
                    e
                )

    @staticmethod
    def get_test_solution_path(solution_file="solution0_dummy.py"):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", solution_file)
        return str(path.resolve())

    def fake_install(self, path, create_environment=True) -> Optional[Solution]:
        # add to local catalog
        loaded_solution = self.album_controller.state_manager().load(path)

        cache_catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )
        if create_environment:
            env_name = "_".join(
                [cache_catalog.name(), loaded_solution.get_identifier()]
            )
            self.album_controller.environment_manager().get_package_manager().install(
                Environment(None, env_name, Path("unusedCachePath"))
            )

        # add to collection, assign to local catalog
        len_catalog_before = len(
            self.album_controller.collection_manager().catalog_collection.get_solutions_by_catalog(
                cache_catalog.catalog_id()
            )
        )
        self.album_controller.collection_manager().solutions().add_to_cache_catalog(
            loaded_solution, path
        )
        self.album_controller.collection_manager().solutions().set_installed(
            cache_catalog, loaded_solution.coordinates()
        )
        self.assertEqual(
            len_catalog_before + 1,
            len(
                self.album_controller.collection_manager().catalog_collection.get_solutions_by_catalog(
                    cache_catalog.catalog_id()
                )
            ),
        )

        # copy to correct folder
        copy(
            path,
            cache_catalog.path().joinpath(
                DefaultValues.catalog_solutions_prefix.value,
                loaded_solution.coordinates().group(),
                loaded_solution.coordinates().name(),
                loaded_solution.coordinates().version(),
                DefaultValues.solution_default_name.value,
            ),
        )
        return loaded_solution
