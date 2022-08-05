# flake8: noqa

import pkg_resources

from . import _filefinder, cmip, utils
from ._filefinder import FileContainer, FileFinder

try:
    __version__ = pkg_resources.get_distribution("regionmask").version
except Exception:
    # Local copy or not installed with setuptools.
    # Disable minimum version checks on downstream libraries.
    __version__ = "999"
