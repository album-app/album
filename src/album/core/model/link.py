"""Link model module."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Windows: another process has the file open, e.g. a virus scanner checking a shortcut just read or written
ERROR_SHARING_VIOLATION = 32
REMOVE_ATTEMPTS = 10
REMOVE_WAIT = 0.5  # seconds between two attempts


class Link(type(Path())):  # type: ignore[misc]
    """Link model implementation."""

    _link = None

    def set_link(self, link: Path) -> Link:
        """Set the link."""
        self._link = link
        return self

    def get_link(self) -> Path | None:
        """Get the link."""
        return self._link

    def dispose(self) -> None:
        """Dispose the link."""
        if self._link:
            link = os.path.normpath(self._link)
            if sys.platform == "win32":
                link += ".lnk"
            if os.path.exists(link) or os.path.islink(link):
                _remove(link)


def _remove(path: str) -> None:
    """Remove a file, trying again for a moment while another process has it open."""
    for attempt in range(1, REMOVE_ATTEMPTS + 1):
        try:
            os.remove(path)
            return
        except PermissionError as e:
            in_use = getattr(e, "winerror", None) == ERROR_SHARING_VIOLATION
            if not in_use or attempt == REMOVE_ATTEMPTS:
                raise
            time.sleep(REMOVE_WAIT)
