import queue
import sys
import threading
from threading import Thread

from album.core.concept.singleton import Singleton
from album.core.model.task import Task, LogHandler
from album.runner import logging

module_logger = logging.get_active_logger


class TaskManager(metaclass=Singleton):
    """Class for retrieving the status of a solution.
    """

    server_queue = None
    num_fetch_threads = 3

    tasks = {}
    task_count = 0
    workers_initialized = False

    def __init__(self):
        self.tasks = {}
        self.task_count = 0
        self.server_queue = queue.Queue()
        self.workers_initialized = False

    def _initialize_workers(self):
        self.workers_initialized = True
        current_thread = threading.current_thread().ident
        module_logger().info(f"TaskManager: Initializing {self.num_fetch_threads} worker threads..")
        for i in range(self.num_fetch_threads):
            worker = Thread(target=self._run_queue_entry, args=(i, current_thread))
            worker.setDaemon(True)
            worker.start()

    def get_task(self, task_id):
        """Get a task managed by the task manager."""
        return self.tasks[task_id]

    def get_status(self, task):
        """Get the status of a task managed by the task manager."""
        return {
            "status": task.status.name,
            "records": self._records_to_json(task.log_handler.records)
        }

    @staticmethod
    def _records_to_json(records):
        res = []
        for record in records:
            res.append({
                "asctime": str(record.asctime),
                "name": str(record.name),
                "levelname": str(record.levelname),
                "msg": str(record.msg),
            })
        return res

    def finish_queue(self):
        self.server_queue.join()
        # TODO add timeout parameter and do something like the following if timeout is set:
        # timeout = 10  # waiting for 10 seconds for queue to finish
        # stop = time() + timeout
        # while self.server.task_manager.server_queue.unfinished_tasks and time() < stop:
        #     sleep(1)

    def register_task(self, task):
        if not self.workers_initialized:
            self._initialize_workers()
        task.id = str(self.task_count)
        module_logger().info(f"TaskManager: registering task {task.id}")
        task.status = Task.Status.WAITING
        self.task_count += 1
        self.tasks[task.id] = task
        self.server_queue.put(task)
        return task.id

    def _run_queue_entry(self, i, parent_thread):
        logging.configure_logging("worker" + str(i), parent_thread_id=parent_thread)
        while True:
            task = self.server_queue.get()
            self._handle_task(task)
            self.server_queue.task_done()

    def _handle_task(self, task):
        module_logger().info(f"TaskManager: starting task {task.id}..")
        logger = logging.configure_logging("task" + str(task.id))
        handler = LogHandler()
        task.log_handler = handler
        logger.addHandler(handler)
        task.status = Task.Status.RUNNING
        try:
            self._run_task(task)
            task.status = Task.Status.FINISHED
        except Exception as e:
            logger.error(e)
            task.status = Task.Status.FAILED
        logger.removeHandler(handler)
        logging.pop_active_logger()
        module_logger().info(f"TaskManager: finished task {task.id}.")

    @staticmethod
    def _run_task(task):
        return task.method(*task.args)

