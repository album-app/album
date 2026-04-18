"""Album core package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("album")
except PackageNotFoundError:
    __version__ = "unknown"

__author__ = "Kyle Harrington, Jan Philipp Albrecht, Deborah Schmidt"
__email__ = "album@kyleharrington.com, album@jpalbrecht.de, mail@frauzufall.de"
