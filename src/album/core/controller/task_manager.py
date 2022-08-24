import queue
import threading
from threading import Thread

from album.core.api.controller.task_manager import ITaskManager
from album.core.api.model.task import ITask
from album.core.model.task import LogHandler, Task
from album.runner import album_logging

module_logger = album_logging.get_active_logger


class TaskManager(ITaskManager):
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
        module_logger().info(
            f"TaskManager: Initializing {self.num_fetch_threads} worker threads..."
        )
        for i in range(self.num_fetch_threads):
            worker = Thread(target=self._run_queue_entry, args=(i, current_thread))
            worker.setDaemon(True)
            worker.start()

    def get_task(self, task_id):
        return self.tasks[task_id]

    def get_status(self, task: ITask):
        return {
            "status": task.status().name,
            "records": self._records_to_json(task.log_handler().records()),
        }

    @staticmethod
    def _records_to_json(records):
        res = []
        for record in records:
            res.append(
                {
                    "asctime": None
                    if not hasattr(record, "asctime")
                    else str(record.asctime),
                    "name": None if not hasattr(record, "name") else str(record.name),
                    "levelname": None
                    if not hasattr(record, "levelname")
                    else str(record.levelname),
                    "msg": None if not hasattr(record, "msg") else str(record.msg),
                }
            )
        return res

    def _finish_queue(self):
        self.server_queue.join()
        # TODO add timeout parameter and do something like the following if timeout is set:
        # timeout = 10  # waiting for 10 seconds for queue to finish
        # stop = time() + timeout
        # while self.server.task_manager.server_queue.unfinished_tasks and time() < stop:
        #     sleep(1)

    def create_and_register_task(self, method, args) -> str:
        task = Task(method, args)
        return self.register_task(task)

    def register_task(self, task: ITask) -> str:
        if not self.workers_initialized:
            self._initialize_workers()
        task.set_id(str(self.task_count))
        module_logger().info(f"TaskManager: registering task {task.id()}")
        task.set_status(ITask.Status.WAITING)
        self.task_count += 1
        self.tasks[task.id()] = task
        self.server_queue.put(task)
        return task.id()

    def _run_queue_entry(self, i, parent_thread):
        album_logging.configure_logging(
            "worker" + str(i), parent_thread_id=parent_thread
        )
        while True:
            task = self.server_queue.get()
            self._handle_task(task)
            self.server_queue.task_done()

    def _handle_task(self, task: ITask):
        module_logger().info(f"TaskManager: starting task {task.id()}...")
        logger = album_logging.configure_logging("task" + str(task.id()))
        handler = LogHandler()
        task.set_log_handler(handler)
        logger.addHandler(handler)
        task.set_status(ITask.Status.RUNNING)
        try:
            self._run_task(task)
            task.set_status(ITask.Status.FINISHED)
        except Exception as e:
            logger.error(e)
            task.set_status(ITask.Status.FAILED)
        logger.removeHandler(handler)
        album_logging.pop_active_logger()
        module_logger().info(f"TaskManager: finished task {task.id()}.")

    def finish_tasks(self):
        self.server_queue.join()

    @staticmethod
    def _run_task(task: ITask):
        return task.method()(*task.args())
