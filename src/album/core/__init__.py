"""Album core package.

album's version and authors are written down in ``pyproject.toml`` only. They
are read here from the metadata of the installed ``album`` distribution, so a
release changes the version in ``pyproject.toml`` and nowhere else.
"""

from email.utils import getaddresses
from importlib.metadata import PackageNotFoundError, metadata
from typing import Iterable, List, Tuple


def _contacts(field_values: Iterable[str]) -> List[Tuple[str, str]]:
    """Return the (name, email) pairs of a metadata field such as ``Author-email``."""
    return [(name, email) for name, email in getaddresses(field_values) if email]


try:
    _metadata = metadata("album")
except PackageNotFoundError:  # a source tree that is not installed
    __version__ = "unknown"
    __author__ = __email__ = ""
else:
    # authors with an email are written to "Author-email", authors without one to "Author"
    _authors = _contacts(_metadata.get_all("Author-email") or [])
    __version__ = _metadata["Version"]
    __author__ = ", ".join(
        [name for name, _ in _authors if name] + (_metadata.get_all("Author") or [])
    )
    __email__ = ", ".join(email for _, email in _authors)
