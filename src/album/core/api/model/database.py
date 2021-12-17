from abc import ABCMeta, abstractmethod
from sqlite3 import Connection, Cursor


class IDatabase:
    __metaclass__ = ABCMeta

    @abstractmethod
    def close_current_connection(self, commit=True):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    def get_connection(self) -> Connection:
        raise NotImplementedError

    @abstractmethod
    def get_cursor(self) -> Cursor:
        raise NotImplementedError

    @abstractmethod
    def next_id(self, table_name, close=False) -> int:
        raise NotImplementedError

    @abstractmethod
    def is_created(self, close: bool = True) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_table_empty(self, table, close: bool = True) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create(self):
        raise NotImplementedError

    @abstractmethod
    def is_empty(self, close: bool = True) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_path(self):
        raise NotImplementedError
