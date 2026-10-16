"""Interface for downloading the resources of solutions and sharing them between solutions."""

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import List, Optional

from album.core.api.model.collection_solution import ICollectionSolution
from album.core.model.replicability import ReplicabilityReason
from album.runner.core.api.model.solution import ISolution


class IDownloadManager:
    """
    Interface handling the file download and sharing locations of files requested by solutions.

    A solution declares its resources in the ``resource_file`` entry of its dependencies. It takes
    the same forms as the ``environment_file``: the content as a string, a url, the path of a .yml
    file (a relative path starts at the folder of the solution), a ``StringIO`` or a dictionary,
    for example:

        resources:
            model:
                name: model.pt
                url: https://example.org/model.pt
                hash: "sha256:9d88224e3be283730af0f4388573eb3019bb0aa40c0b77a8350019fb34afe9d8"
                scope: catalog
            viewer:
                name: viewer-linux-x64.tar.xz
                url: https://example.org/viewer-linux-x64.tar.xz
                os: linux
                scope: solution

    Only ``name`` and ``url`` are required. The ``hash`` pins the content of a resource, a
    download with a different content fails. A resource with an ``os`` (``linux``, ``win32`` or
    ``darwin``) is only downloaded on that platform. The ``scope`` decides who shares a resource:
    all solutions (``global``, the default), the solutions of the same catalog (``catalog``) or
    nobody (``solution``, removed with the solution).
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def download_resources(
        self, collection_solution: ICollectionSolution
    ) -> Optional[Path]:
        """
        Download the resources of a solution that are meant for the current platform.

        A shared resource is stored in a folder named after its content, so solutions only share
        a file when they ask for the same content. The paths of all resources are written to a
        json file in the internal cache of the solution, where the solution reads them with
        ``get_resources_dict()``. Resources for other platforms get no path.

        Returns:
            The path of the json file, or None if the solution declares no resources.

        Raises:
            TypeError: if the resource file has none of the accepted forms.
            ValueError: if the content of the resource file is invalid.
            RuntimeError: if a resource cannot be downloaded or does not match its hash.
        """
        raise NotImplementedError

    @abstractmethod
    def check_resources(
        self, solution: ISolution, solution_folder: Optional[Path] = None
    ) -> List[ReplicabilityReason]:
        """
        Check the resource file of a solution before it is deployed.

        Raises the same errors as the installation would for an invalid resource file. A
        relative path of the resource file starts at solution_folder, the folder of the
        solution. Warns about a resource from a url, which can become unavailable.

        Returns:
            What keeps the resources from being technically replicable: a resource without a
            hash, and, only deployed with --no-replicability, one from a url without a hash.
        """
        raise NotImplementedError
