from time import time, sleep
from unittest.mock import patch

from album.core.controller.task_manager import TaskManager
from album.core.model.task import Task
from test.integration.test_integration_core_common import TestIntegrationCoreCommon


class TestIntegrationTaskManager(TestIntegrationCoreCommon):
    def setUp(self):
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

    @patch("album.core.controller.conda_manager.CondaManager.get_environment_path")
    def test_run_happy_solution(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        solution_path = self.get_test_solution_path()
        self.fake_install(solution_path, create_environment=False)
        resolve_result = self.album_controller.collection_manager().resolve_and_load(
            solution_path
        )
        task = Task()
        task._method = self.album_controller.run_manager().run
        task._args = [
            resolve_result.coordinates().group()
            + ":"
            + resolve_result.coordinates().name()
            + ":"
            + resolve_result.coordinates().version()
        ]
        task_manager = TaskManager()
        task_id = task_manager.register_task(task)
        self.assertEqual("0", task_id)
        self.assertEqual(task, task_manager.get_task(task_id))
        self._finish_taskmanager_with_timeout(task_manager, 30)
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
        status = task_manager.get_status(task)
        # print(self.captured_output.getvalue())
        self.assertEqual("FINISHED", status.get("status"))
        self.assertEqual(Task.Status.FINISHED, task.status())

    @patch("album.core.controller.conda_manager.CondaManager.get_environment_path")
    def test_run_sad_solution(self, get_environment_path):
        get_environment_path.return_value = (
            self.album_controller.environment_manager()
            .get_package_manager()
            .get_active_environment_path()
        )
        solution_path = self.get_test_solution_path("solution9_throws_exception.py")
        self.fake_install(solution_path, create_environment=False)
        resolve_result = self.album_controller.collection_manager().resolve_and_load(
            solution_path
        )
        task = Task()
        task.method = self.album_controller.run_manager().run
        task.args = [
            resolve_result.coordinates().group()
            + ":"
            + resolve_result.coordinates().name()
            + ":"
            + resolve_result.coordinates().version()
        ]
        task_manager = TaskManager()
        task_manager.register_task(task)
        self._finish_taskmanager_with_timeout(task_manager, 30)
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
        status = task_manager.get_status(task)
        self.assertEqual("FAILED", status.get("status"))
        self.assertEqual(Task.Status.FAILED, task.status())

    def _finish_taskmanager_with_timeout(self, task_manager, timeout):
        # since queue.join has no timeout, we are doing something else to check if the queue is processed
        # self.server.task_manager.server_queue.join()
        stop = time() + timeout
        while task_manager.server_queue.unfinished_tasks and time() < stop:
            sleep(1)
        # make sure tasks are finished
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
