import os
from pathlib import Path
from test.test_common import TestCommon
from typing import Optional

from album.core.utils.operations.file_operations import copy
from album.runner.core.api.model.solution import ISolution


class TestIntegrationCoreCommon(TestCommon):
    def setUp(self):
        super().setUp()
        self.setup_album_controller()
        self.setup_collection()

    def tearDown(self) -> None:
        super().tearDown()

    @staticmethod
    def get_test_solution_path(solution_file="solution0_dummy.py"):
        current_path = Path(os.path.dirname(os.path.realpath(__file__)))
        path = current_path.joinpath("..", "resources", solution_file)
        return str(path.resolve())

    def fake_install(self, path, create_environment=True) -> Optional[ISolution]:
        # add to local catalog
        solution = self.album_controller.collection_manager().resolve_and_load(path)
        cache_catalog = (
            self.album_controller.collection_manager().catalogs().get_cache_catalog()
        )

        if create_environment:
            self.album_controller.environment_manager().install_environment(solution)

        # add to collection, assign to local catalog
        len_catalog_before = len(
            self.album_controller.collection_manager().catalog_collection.get_solutions_by_catalog(
                cache_catalog.catalog_id()
            )
        )
        self.album_controller.collection_manager().solutions().add_to_cache_catalog(
            solution
        )
        self.album_controller.collection_manager().solutions().set_installed(
            cache_catalog, solution.coordinates()
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
            self.album_controller.solutions().get_solution_file(
                cache_catalog, solution.coordinates()
            ),
        )
        return solution.loaded_solution()
