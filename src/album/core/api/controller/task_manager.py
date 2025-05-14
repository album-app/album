"""Interface for a task manager."""
from abc import ABCMeta, abstractmethod
from typing import Callable, Dict, List, Optional, Union

from album.core.api.model.task import ITask


class ITaskManager:
    """Interface for retrieving the status of a solution."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_task(self, task_id: str) -> ITask:
        """Get a task managed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self, task: ITask) -> Dict[str, Union[str, List[Dict[str, str]]]]:
        """Get the status of a task managed by the task manager."""
        raise NotImplementedError

    @abstractmethod
    def create_and_register_task(
        self, method: Callable, args: Optional[List[str]]
    ) -> str:
        """Create a task and register it with the task manager."""
        raise NotImplementedError

    @abstractmethod
    def register_task(self, task: ITask) -> str:
        """Register a task with the task manager."""
        raise NotImplementedError

    @abstractmethod
    def finish_tasks(self) -> None:
        """Finish all tasks managed by the task manager."""
        raise NotImplementedError
