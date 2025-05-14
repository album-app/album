import platform
import sys
import threading
import unittest.mock
from threading import Thread
from time import sleep

from album.core.controller.task_manager import TaskManager
from album.core.model.task import Task
from album.environments.utils import subcommand
from album.runner import album_logging
from album.runner.album_logging import LogLevel
from test.unit.test_unit_core_common import TestUnitCoreCommon


class TestTaskManager(TestUnitCoreCommon):
    def test_handle_task(self):
        album_logging.set_loglevel(LogLevel.INFO)
        task = Task(self._log_to_active_logger)
        task._id = 0
        task_manager = TaskManager()
        task_manager._handle_task(task)
        self.assertEqual(1, len(task.log_handler().records()))
        self.assertEqual("test", task.log_handler().records()[0].msg)

    def test_register_task(self):

        album_logging.set_loglevel(LogLevel.INFO)

        task = Task(self._log_to_active_logger)

        task_manager = TaskManager()

        task_manager.register_task(task)
        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        task_manager._finish_queue()
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

        self.assertEqual(1, len(task.log_handler().records()))
        self.assertEqual("test", task.log_handler().records()[0].msg)

    def test_register_task_in_thread(self):

        album_logging.set_loglevel(LogLevel.INFO)

        task = Task(self._log_to_active_logger_via_thread)

        task_manager = TaskManager()

        task_manager.register_task(task)
        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        task_manager._finish_queue()
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

        self.assertEqual(1, len(task.log_handler().records()))
        self.assertEqual("test", task.log_handler().records()[0].msg)

    @unittest.skipIf(sys.platform == "darwin", "FIXME Logs missing on MacOS")
    def test_register_task_in_subcommand(self):

        album_logging.set_loglevel(LogLevel.DEBUG)

        task = Task(self._log_to_active_logger_via_subcommand)

        task_manager = TaskManager()

        task_manager.register_task(task)
        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        task_manager._finish_queue()
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

        for record in task.log_handler().records():
            print(record.msg)
        self.assertTrue(len(task.log_handler().records()) > 1)
        if platform.system() == "Windows":
            self.assertEqual(
                "Running command: cmd /c echo test...",
                task.log_handler().records()[0].msg,
            )
        else:
            self.assertEqual(
                "Running command: echo test...", task.log_handler().records()[0].msg
            )
        self.assertEqual("test", task.log_handler().records()[1].msg)

    def _log_to_active_logger_via_thread(self):
        thread = Thread(
            target=self._log_to_active_logger_in_thread,
            args=(threading.current_thread().ident,),
        )
        thread.start()
        thread.join()

    @staticmethod
    def _log_to_active_logger_via_subcommand():
        if platform.system() == "Windows":
            subcommand.run(["cmd", "/c", "echo test"])
        else:
            subcommand.run(["echo", "test"])
        sleep(0.1)

    @staticmethod
    def _log_to_active_logger():
        album_logging.configure_logging("test", loglevel=LogLevel.INFO)
        album_logging.get_active_logger().info("test")
        album_logging.pop_active_logger()

    @staticmethod
    def _log_to_active_logger_in_thread(parent_thread_id):
        album_logging.configure_logging(
            "test", loglevel=LogLevel.INFO, parent_thread_id=parent_thread_id
        )
        album_logging.get_active_logger().info("test")
        album_logging.pop_active_logger()


if __name__ == "__main__":
    unittest.main()
