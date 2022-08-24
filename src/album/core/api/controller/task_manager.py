from abc import ABCMeta, abstractmethod

from album.core.api.model.task import ITask


class ITaskManager:
    """Interface for retrieving the status of a solution."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_task(self, task_id) -> ITask:
        """Get a task managed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, task) -> ITask.Status:
        """Get the status of a task managed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def create_and_register_task(self, method, args) -> str:
        raise NotImplementedError

    @abstractmethod
    def register_task(self, task: ITask) -> str:
        raise NotImplementedError

    @abstractmethod
    def finish_tasks(self):
        raise NotImplementedError
