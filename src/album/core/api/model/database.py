"""Module defining a database interface."""
from abc import ABCMeta, abstractmethod
from pathlib import Path
from sqlite3 import Connection, Cursor


class IDatabase:
    """Interface for a database."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def close_current_connection(self, commit: bool = True) -> None:
        """Close the current connection."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close the database."""
        raise NotImplementedError

    @abstractmethod
    def get_connection(self) -> Connection:
        """Get a connection to the database."""
        raise NotImplementedError

    @abstractmethod
    def get_cursor(self) -> Cursor:
        """Get a cursor to the database."""
        raise NotImplementedError

    @abstractmethod
    def next_id(self, table_name, close=False) -> int:
        """Get the next id for a table."""
        raise NotImplementedError

    @abstractmethod
    def is_created(self, close: bool = True) -> bool:
        """Check if the database is created."""
        raise NotImplementedError

    @abstractmethod
    def is_table_empty(self, table, close: bool = True) -> bool:
        """Check if a table is empty."""
        raise NotImplementedError

    @abstractmethod
    def create(self) -> None:
        """Create the database."""
        raise NotImplementedError

    @abstractmethod
    def is_empty(self, close: bool = True) -> bool:
        """Check if the database is empty."""
        raise NotImplementedError

    @abstractmethod
    def get_path(self) -> Path:
        """Get the path to the database."""
        raise NotImplementedError
