from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from album.core.api.model.collection_solution import ICollectionSolution


class IDownloadManager:
    """
    Interface handling the file download and sharing locations of files requested by solutions.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def download_resources_from_yaml(self, solution: ICollectionSolution) -> bool:
        """
        Downloads the resources of a solution that are specified in the solution's YAML file.

        In the following example resource yaml, the path where the resource should be stored is dependent on the scope, e.g. a resource with scope `solution` should be stored in the solution folder of the app_path.
        Only fitting OS resources should be stored and downloaded.
        When no scope is given, it will be in the global shared_downloads folder.
        Example:
        resource_yaml = '''
        resources:
            file1:
                name: blender-3.3.1-linux-x64.tar.xz
                url: https://download.blender.org/release/Blender3.3/blender-3.3.1-linux-x64.tar.xz
                hash:
                os: linux
                scope: catalog

            file2:
                name: blender-3.3.1-windows-x64.zip
                url: https://download.blender.org/release/Blender3.3/blender-3.3.1-windows-x64.zip
                hash: md5:1234
                os: win32
                scope: solution

            file3:
                name: blender-3.3.1-macos-x64.dmg
                url: https://download.blender.org/release/Blender3.3/blender-3.3.1-macos-x64.dmg
                hash: sha256:1234
                os: darwin
        '''

        """
        raise NotImplementedError

    @abstractmethod
    def get_download_paths(
        self, collection_solution: ICollectionSolution
    ) -> Tuple[Dict[str, Any], Path]:
        """
        Converts a resource YAML to a dictionary and inserts the download paths of the resources to the dictionary.
        """
        raise NotImplementedError

    @staticmethod
    def clean_up_downloads(
        scope_to_clear: str, catalog_name: Optional[str] = None
    ) -> bool:
        """
        Removes all downloaded resources of specified scope. Either `global`or `catalog` to remove shared resources. SOlution resources will be removed upon uninstallation.
        """
        raise NotImplementedError
