from abc import ABCMeta, abstractmethod


class TaskInterface:
    """Interface for retrieving the status of a solution.
        """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_task(self, task_id):
        """Get a task managed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, task):
        """Get the status of a task managed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def register_task(self, task):
        raise NotImplementedError

    @abstractmethod
    def finish_tasks(self):
        raise NotImplementedError

