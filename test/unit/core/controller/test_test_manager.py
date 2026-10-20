import unittest.mock
from pathlib import Path
from test.unit.test_unit_core_common import TestUnitCoreCommon
from unittest.mock import MagicMock

from album.core.model.resolve_result import ResolveResult
from album.runner.core.api.model.solution import ISolution
from album.runner.core.model.solution import Solution


class TestTestManager(TestUnitCoreCommon):
    def setUp(self):
        super().setUp()
        self.setup_collection()

    def _prepare(self, **routines):
        solution_dict = self.get_solution_dict()
        solution_dict.update(routines)
        solution = Solution(solution_dict)
        self.resolve_result = ResolveResult(
            path=Path("aPath"),
            catalog=None,
            collection_entry=None,
            coordinates=solution.coordinates(),
            loaded_solution=solution,
        )

        # mocks
        self.album_controller.collection_manager().resolve_installed_and_load = (
            MagicMock(return_value=self.resolve_result)
        )
        self.build_queue = MagicMock()
        self.album_controller.script_manager().build_queue = self.build_queue
        self.run_queue = MagicMock()
        self.album_controller.script_manager().run_queue = self.run_queue

    def test_test(self):
        self._prepare(test=lambda: None)

        # call
        self.album_controller.test_manager().test("tsg:tsn:tsv", ["", "--a=1"])

        # assert
        self.build_queue.assert_called_once_with(
            self.resolve_result,
            unittest.mock.ANY,
            ISolution.Action.TEST,
            False,
            ["", "--a=1"],
        )
        self.run_queue.assert_called_once()
        self.assertIn('Ran test routine for "tsn"!', self.get_logs_as_string())

    def test_test_with_pre_test(self):
        self._prepare(test=lambda: None, pre_test=lambda: {})

        # call
        self.album_controller.test_manager().test("tsg:tsn:tsv")

        # assert
        self.build_queue.assert_called_once_with(
            self.resolve_result, unittest.mock.ANY, ISolution.Action.TEST, False, [""]
        )
        self.run_queue.assert_called_once()

    def test_test_no_test_routine(self):
        for routines in [{}, {"pre_test": lambda: {}}, {"test": "not callable"}]:
            with self.subTest(routines=routines):
                self._prepare(**routines)

                # call
                self.album_controller.test_manager().test("tsg:tsn:tsv")

                # assert
                self.build_queue.assert_not_called()
                self.run_queue.assert_not_called()
                self.assertIn(
                    'No "test" routine configured for solution "tsn"! Skipping...',
                    self.get_logs()[-1],
                )

    def test_test_pre_test_not_callable(self):
        self._prepare(test=lambda: None, pre_test="not callable")

        # call
        self.album_controller.test_manager().test("tsg:tsn:tsv")

        # assert: skipped, the runner would fail calling "pre_test"
        self.build_queue.assert_not_called()
        self.run_queue.assert_not_called()
        self.assertIn(
            'The "pre_test" routine of solution "tsn" is not callable! Skipping...',
            self.get_logs()[-1],
        )


if __name__ == "__main__":
    unittest.main()
