from .__version__ import __version__
from .launcher import entry_point
from .shell import set_process_appid, install, uninstall

__all__ = [
    'entry_point',
    'set_process_appid',
    'install',
    'uninstall',
]
