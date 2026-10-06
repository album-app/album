from pathlib import Path
from test.test_common import TEST_ALBUM_API_VERSION
from test.unit.test_unit_core_common import TestUnitCoreCommon

from album.core.controller.state_manager import StateManager


class TestStateManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.state_manager: StateManager = self.album_controller.state_manager()

    def tearDown(self) -> None:
        super().tearDown()

    def test_load_utf8_solution_file(self):
        description = "Zellkerngröße in µm (顕微鏡)"
        solution_file = Path(self.tmp_dir.name).joinpath("solution.py")
        # solution files are UTF-8, independent of the platform default encoding
        solution_file.write_bytes(
            (
                "from album.runner.api import setup\n"
                "\n"
                "setup(\n"
                '    group="group",\n'
                '    name="name",\n'
                '    version="0.1.0",\n'
                '    description="%s",\n'
                '    album_api_version="%s",\n'
                ")\n" % (description, TEST_ALBUM_API_VERSION)
            ).encode("utf-8")
        )

        solution = self.state_manager.load(str(solution_file))

        self.assertEqual(description, solution.setup()["description"])
        self.assertEqual(str(solution_file), solution.script())
