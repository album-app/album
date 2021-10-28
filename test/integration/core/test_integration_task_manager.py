import unittest
import urllib.parse
from pathlib import Path
from time import time, sleep
from unittest.mock import patch

import flask_unittest
from album.core.controller.conda_manager import CondaManager

from album.core.controller.run_manager import RunManager

from album.core.controller.task_manager import TaskManager

from album.core.model.coordinates import Coordinates
from album.core.model.default_values import DefaultValues
from album.core.model.task import Task
from album.core.server import AlbumServer
from album.runner import logging
from album.runner.logging import LogLevel
from test.integration.test_integration_common import TestIntegrationCommon


class TestIntegrationTaskManager(TestIntegrationCommon):

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_happy_solution(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        solution_path = self.get_test_solution_path()
        self.fake_install(solution_path, create_environment=False)
        task = Task()
        task.method = RunManager().run
        task.args = [solution_path]
        task_manager = TaskManager()
        id = task_manager.register_task(task)
        self.assertEqual("0", id)
        self.assertEqual(task, task_manager.get_task(id))
        self._finish_taskmanager_with_timeout(task_manager, 30)
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
        status = TaskManager().get_status(task)
        self.assertEqual("FINISHED", status.get("status"))
        self.assertEqual(Task.Status.FINISHED, task.status)

    @patch('album.core.controller.conda_manager.CondaManager.get_environment_path')
    def test_run_sad_solution(self, get_environment_path):
        get_environment_path.return_value = CondaManager().get_active_environment_path()
        solution_path = self.get_test_solution_path("solution9_throws_exception.py")
        self.fake_install(solution_path, create_environment=False)
        task = Task()
        task.method = RunManager().run
        task.args = [solution_path]
        task_manager = TaskManager()
        task_manager.register_task(task)
        self._finish_taskmanager_with_timeout(task_manager, 30)
        self.assertFalse(task_manager.server_queue.unfinished_tasks)
        status = TaskManager().get_status(task)
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
