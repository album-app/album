"""This module contains the Interface for a Version."""
from abc import ABCMeta, abstractmethod


class IMMVersion:
    """Class to make versions (with mayor and minor versions) comparable.

    Transforms the "x.x.x" version strings used in album into comparable integers.

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def __eq__(self, other):
        """Equality operator for MMVersion objects."""
        raise NotImplementedError

    @abstractmethod
    def __lt__(self, other):
        """Less than operator for MMVersion objects."""
        raise NotImplementedError

    @abstractmethod
    def __gt__(self, other):
        """Greater than operator for MMVersion objects."""
        raise NotImplementedError

    @abstractmethod
    def __str__(self):
        """Return the version as string."""
        raise NotImplementedError

    @classmethod
    def from_string(cls, version_string):
        """Create a MMVersion object from a string."""
        raise NotImplementedError

    @classmethod
    def from_sql_schema_name(cls, sql_schema_name):
        """Return the target version of a given sql schema name."""
        raise NotImplementedError
