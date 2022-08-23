import os
import platform
from pathlib import Path


class Link(type(Path())):
    _flavour = type(Path())._flavour
    _link = None

    def set_link(self, link):
        self._link = link
        return self

    def get_link(self):
        return self._link

    def dispose(self):
        if self._link:
            operation_system = platform.system().lower()
            link = os.path.normpath(self._link)
            if "windows" in operation_system:
                link += ".lnk"
            if os.path.exists(link) or os.path.islink(link):
                os.remove(link)
