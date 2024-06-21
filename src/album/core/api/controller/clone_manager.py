"""Interface handling the creation of new catalogs and solutions."""
from abc import ABCMeta, abstractmethod
from typing import Optional


class ICloneManager:
    """Interface handling the creation of new catalogs and solutions."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def clone(
        self,
        path: str,
        target_dir: str,
        name: str,
        git_email: Optional[str] = None,
        git_name: Optional[str] = None,
    ) -> None:
        """Clone a template or solution.

        Args:
            path:
                The source of the clone command - a solution (group:name:version, path, or URL to file) or a catalog
                template string (i.e. template:catalog).
            target_dir:
                The directory where the cloned solution or catalog will be added to.
            name:
                The name of the solution or catalog to be created.
            git_email:
                (catalog cloning only) email of the git user to be used for pushing to target_dir
                (in case it's already a git repo).
            git_name:
                (catalog cloning only) name of the git user to be used for pushing to target_dir
                (in case it's already a git repo).

        """
        raise NotImplementedError
