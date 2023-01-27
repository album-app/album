from abc import ABCMeta, abstractmethod


class IDBVersion:

    """Class to make database versions comparable
        transforms the \"x.x.x\" version strings used in album into comparable integers
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def __eq__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __lt__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __gt__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __str__(self):
        """Returns the version string"""
        raise NotImplementedError

    @classmethod
    def from_string(cls, version_string):
        """Create a DBVersion object from a string"""
        raise NotImplementedError

    @classmethod
    def from_sql_schema_name(cls, sql_schema_name):
        """Returns the target version of a given sql schema name"""
        raise NotImplementedError
