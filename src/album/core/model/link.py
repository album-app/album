"""Link model module."""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Optional


class Link(type(Path())):
    """Link model implementation."""

    _flavour = type(Path())._flavour
    _link = None

    def set_link(self, link: Path) -> Link:
        """Set the link."""
        self._link = link
        return self

    def get_link(self) -> Optional[Path]:
        """Get the link."""
        return self._link

    def dispose(self) -> None:
        """Dispose the link."""
        if self._link:
            operation_system = platform.system().lower()
            link = os.path.normpath(self._link)
            if "windows" in operation_system:
                link += ".lnk"
            if os.path.exists(link) or os.path.islink(link):
                os.remove(link)
