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
    def __le__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __ge__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __str__(self):
        raise NotImplementedError
