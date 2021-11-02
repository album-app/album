import threading
import unittest.mock
from threading import Thread

from album.core.controller.task_manager import TaskManager
from album.core.model.task import Task
from album.core.utils import subcommand
from album.runner import album_logging
from album.runner.album_logging import LogLevel
from test.unit.test_unit_common import TestUnitCommon


class TestTaskManager(TestUnitCommon):

    def test_handle_task(self):
        album_logging.set_loglevel(LogLevel.INFO)
        task = Task()
        task.id = 0
        task.method = self._log_to_active_logger
        task_manager = TaskManager()
        task_manager._handle_task(task)
        self.assertEqual(1, len(task.log_handler.records))
        self.assertEqual("test", task.log_handler.records[0].msg)

    def test_register_task(self):

        album_logging.set_loglevel(LogLevel.INFO)

        task = Task()
        task.method = self._log_to_active_logger

        task_manager = TaskManager()

        task_manager.register_task(task)
        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        task_manager.finish_queue()
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

        self.assertEqual(1, len(task.log_handler.records))
        self.assertEqual("test", task.log_handler.records[0].msg)

    def test_register_task_in_thread(self):

        album_logging.set_loglevel(LogLevel.INFO)

        task = Task()
        task.method = self._log_to_active_logger_via_thread

        task_manager = TaskManager()

        task_manager.register_task(task)
        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        task_manager.finish_queue()
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

        self.assertEqual(1, len(task.log_handler.records))
        self.assertEqual("test", task.log_handler.records[0].msg)

    def test_register_task_in_subcommand(self):

        album_logging.set_loglevel(LogLevel.DEBUG)

        task = Task()
        task.method = self._log_to_active_logger_via_subcommand

        task_manager = TaskManager()

        task_manager.register_task(task)
        self.assertTrue(task_manager.server_queue.unfinished_tasks)

        task_manager.finish_queue()
        self.assertFalse(task_manager.server_queue.unfinished_tasks)

        for record in task.log_handler.records:
            print(record.msg)
        self.assertTrue(len(task.log_handler.records) > 1)
        self.assertEqual("Running command: echo test...", task.log_handler.records[0].msg)
        self.assertEqual("test", task.log_handler.records[1].msg)

    def _log_to_active_logger_via_thread(self):
        thread = Thread(target=self._log_to_active_logger_in_thread, args=(threading.current_thread().ident, ))
        thread.start()
        thread.join()

    def _log_to_active_logger_via_subcommand(self):
        subcommand.run(["echo", "test"])

    def _log_to_active_logger(self):
        album_logging.configure_logging("test", loglevel=LogLevel.INFO)
        album_logging.get_active_logger().info("test")
        album_logging.pop_active_logger()

    def _log_to_active_logger_in_thread(self, parent_thread_id):
        album_logging.configure_logging("test", loglevel=LogLevel.INFO, parent_thread_id=parent_thread_id)
        album_logging.get_active_logger().info("test")
        album_logging.pop_active_logger()


if __name__ == '__main__':
    unittest.main()
