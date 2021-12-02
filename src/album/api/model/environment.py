from abc import ABCMeta, abstractmethod


class IEnvironment:
    """Interface managing an environment a solution lives in.

    Each solution lives in its own environment having different dependencies. These can be libraries, programs, etc.
    Each environment has its own environment path and is identified by such. Each album environment has to have
    the album-runner installed for the album framework to be able to run the solution in its environment.
    An environment can be set up by environment file or only by name.

    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def name(self):
        raise NotImplementedError

    @abstractmethod
    def cache_path(self):
        raise NotImplementedError

    @abstractmethod
    def yaml_file(self):
        raise NotImplementedError

    @abstractmethod
    def path(self):
        raise NotImplementedError

    @abstractmethod
    def set_path(self, path):
        raise NotImplementedError
