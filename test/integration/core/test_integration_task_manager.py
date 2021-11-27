import unittest
from time import time, sleep
from unittest.mock import patch

from album.core.model.task import Task
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTaskManager(TestIntegrationCommon):

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_happy_solution(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        solution_path = self.get_test_solution_path()
        self.fake_install(solution_path, create_environment=False)
        task = Task()
        task.method = self.album_instance.run_manager().run
        task.args = [solution_path]
        task_manager = self.album_instance.task_manager()
        id = task_manager.register_task(task)
        self.assertEqual("0", id)
        self.assertEqual(task, task_manager.get_task(id))
        self._finish_taskmanager_with_timeout(task_manager, 30)
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
        status = task_manager.get_status(task)
        self.assertEqual("FINISHED", status.get("status"))
        self.assertEqual(Task.Status.FINISHED, task.status)

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_sad_solution(self, get_environment_path):
        get_environment_path.return_value = self.album_instance.environment_manager().get_conda_manager().get_active_environment_path()
        solution_path = self.get_test_solution_path("solution9_throws_exception.py")
        self.fake_install(solution_path, create_environment=False)
        task = Task()
        task.method = self.album_instance.run_manager().run
        task.args = [solution_path]
        task_manager = self.album_instance.task_manager()
        task_manager.register_task(task)
        self._finish_taskmanager_with_timeout(task_manager, 30)
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
        status = task_manager.get_status(task)
        self.assertEqual("FAILED", status.get("status"))
        self.assertEqual(Task.Status.FAILED, task.status)

    def _finish_taskmanager_with_timeout(self, task_manager, timeout):
        # since queue.join has no timeout, we are doing something else to check if the queue is processed
        # self.server.task_manager.server_queue.join()
        stop = time() + timeout
        while task_manager.server_queue.unfinished_tasks and time() < stop:
            sleep(1)
        # make sure tasks are finished
        self.assertFalse(task_manager.server_queue.unfinished_tasks)


if __name__ == '__main__':
    unittest.main()
