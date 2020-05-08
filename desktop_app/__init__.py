import setuptools_scm
from pathlib import Path

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

try:
    __version__ = setuptools_scm.get_version(Path(__file__).parent)
except LookupError:
    try:
        __version__ = importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:
        __version__ = None


from .launcher import entry_point

from .shell import set_process_appid, install, uninstall


__all__ = [
    'entry_point',
    'set_process_appid',
    'install',
    'uninstall',
]
