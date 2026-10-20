import threading
import time
from pathlib import Path
from test.test_common import TEST_ALBUM_API_VERSION
from test.unit.test_unit_core_common import TestUnitCoreCommon

from album.core.controller.album_controller import AlbumController
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

    def _write_solution(self, name: str, sleep: float = 0) -> str:
        path = Path(self.tmp_dir.name).joinpath("%s.py" % name)
        path.write_text(
            "import time\n"
            "\n"
            "from album.runner.api import setup\n"
            "\n"
            'setup(group="group", name="%s", version="0.1.0", album_api_version="%s")\n'
            "time.sleep(%s)\n" % (name, TEST_ALBUM_API_VERSION, sleep),
            encoding="utf-8",
        )
        return str(path)

    def test_load_in_parallel(self):
        # e.g. two threads installing solutions with the same album instance. The first
        # file is still executed while the second one calls setup().
        paths = {
            "first": self._write_solution("first", sleep=0.3),
            "second": self._write_solution("second", sleep=0.6),
        }
        loaded = {}

        def load(name):
            loaded[name] = self.state_manager.load(paths[name]).coordinates().name()

        first = threading.Thread(target=load, args=("first",))
        second = threading.Thread(target=load, args=("second",))
        first.start()
        time.sleep(0.1)
        second.start()
        first.join(10)
        second.join(10)

        # every load returns the solution of its file
        self.assertEqual({"first": "first", "second": "second"}, loaded)
        self.assertEqual([], self.state_manager._active_solution)

    def test_load_with_another_album_instance(self):
        # each one sets the setup() called by solution files to its own
        other_controller = AlbumController(
            base_cache_path=Path(self.tmp_dir.name).joinpath("other")
        )
        self.addCleanup(other_controller.close)
        other_state_manager = other_controller.state_manager()

        # call
        solution = self.state_manager.load(self._write_solution("first"))
        other_solution = other_state_manager.load(self._write_solution("second"))

        # assert
        self.assertEqual("first", solution.coordinates().name())
        self.assertEqual("second", other_solution.coordinates().name())
        self.assertEqual([], self.state_manager._active_solution)
        self.assertEqual([], other_state_manager._active_solution)
