# flake8: noqa

from importlib.metadata import version as _get_version

from . import _filefinder, cmip, utils
from ._filefinder import FileContainer, FileFinder

try:
    __version__ = _get_version("filefinder")
except Exception:  # pragma: no cover
    # Local copy or not installed with setuptools.
    # Disable minimum version checks on downstream libraries.
    __version__ = "999"
