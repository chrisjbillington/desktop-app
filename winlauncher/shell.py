import sys
import os
import sysconfig
import hashlib
import json
from pathlib import Path

if os.name == 'nt':
    from win32com.shell import shellcon
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon

from .utils import get_package_directory


CONFIG_FILENAME = 'winlauncher.json'


class _Module:
    """Object for managing shortcut creation and Windows AppUserModelID configuration
    for a a Python module that has a winlauncher configuration."""

    _instances = {}

    @classmethod
    def instance(cls, module_name):
        """Get an existing instance, if any, or create one and return it."""
        if module_name not in cls._instances:
            cls._instances[module_name] = cls(module_name)
        return cls._instances[module_name]

    def __init__(self, module_name):
        self.module_name = module_name
        self.package_directory = get_package_directory(module_name)
        config = self._load_config()
        self.company_name = config['company_name']
        self.product_name = config.get('product_name', None)
        module_config = config['modules'][module_name]
        self.display_name = module_config.get('display_name', module_name)
        self.ico_file = module_config.get(
            'ico', Path(self.package_directory, f'{module_name}.ico')
        )
        self.svg_file = module_config.get(
            'svg', Path(self.package_directory, f'{module_name}.svg')
        )
        self.launcher_script_path = self._get_launcher_script_path()
        self.appid = self._get_appid()

    def _load_config(self):
        """Load 'winlauncher.json' from the module package directory and return it"""
        with open(Path(self.package_directory, CONFIG_FILENAME)) as f:
            return json.load(f)

    def _get_launcher_script_path(self):
        """Get the path to the script for launching the app without a console. It is
        assumed to be called <module_name> and be in the bin or Scripts directory of the
        current Python interpreter as returned by `sysconfig.get_path('scripts')`. As
        such it will not be correct when used with `pip install --user` or any other
        custom options to pip that modify the install prefix."""
        # Look up the path to the launcher:
        script_path = str(
            Path(sysconfig.get_path('scripts'), self.module_name).absolute()
        )
        if os.name == 'nt':
            return script_path + 'w.exe'
        return script_path

    def _get_appid(self):
        """ Create a string identifying the application, for use in OS interfaces such
        as as a Windows AppUserModelID, or for the name of a Linux .desktop file. The
        format we use in either case is:

        CompanyName.ProductName.<CamelCaseModuleName>.Python-<hexdigits>

        ProductName is omitted if it was not present in the configuration. The last
        field contains a hash of the path to the Python interpreter for the module,
        ensuring the appid is unique to the Python environment. The module name is
        converted to camel case, periods replaced with hyphens and underscores removed.
        """

        # Hash the path to the Python interpreter so that we can include in the appid a
        # segment unique to the Python environment. Note the case-insensitivity - I've
        # observed the case differing depending on whether a virtualenv is active, so
        # better use normpath to not vary with changes in case:
        interpreter_hash = hashlib.sha256(
            os.fsencode(os.path.normcase(sys.executable))
        ).hexdigest()[:16]

        camelcase_modulename = ''.join(
            s.capitalize()
            for s in self.module_name.title().replace('_', '').replace('.', '-')
        )

        appid_parts = [
            self.company_name,
            camelcase_modulename,
            f'Python-{interpreter_hash}',
        ]

        if self.product_name is not None:
            appid_parts.insert(1, self.product_name)

        return '.'.join(appid_parts)

    def set_window_appusermodel_id(self, window_id):
        """Set the Windows AppUserModelID settings for the given `window_id` to the
        appid for the module."""
        store = propsys.SHGetPropertyStoreForWindow(
            window_id, propsys.IID_IPropertyStore
        )
        properties = {
            pscon.PKEY_AppUserModel_ID: self.appid,
            pscon.PKEY_AppUserModel_RelaunchCommand: self.launcher_script_path,
            pscon.PKEY_AppUserModel_RelaunchDisplayNameResource: self.display_name,
            pscon.PKEY_AppUserModel_RelaunchIconResource: self.ico_file,
        }

        for key, value in properties.items():
            store.SetValue(key, propsys.PROPVARIANTType(value))
        store.Commit()

    def add_to_start_menu(self):
        """Add a shortcut the the launcher to the start menu. Windows only."""

        objShell = Dispatch('WScript.Shell')
        start_menu = objShell.SpecialFolders("Programs")

        shortcut_path = os.path.join(start_menu, self.display_name) + '.lnk'
        # Overwrite previously existing shortcuts of the same name:
        if os.path.exists(shortcut_path):
            os.unlink(shortcut_path)

        shortcut = objShell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = self.launcher_script_path
        shortcut.WorkingDirectory = str(Path('~').expanduser)
        shortcut.IconLocation = self.ico_file
        shortcut.Description = self.display_name
        shortcut.save()

        # Edit the shortcut to associate the AppUserModel_ID with it:
        store = propsys.SHGetPropertyStoreFromParsingName(
            shortcut_path, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
        )
        store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(self.appid))
        store.Commit()

    def remove_from_start_menu(self):
        objShell = Dispatch('WScript.Shell')
        start_menu = objShell.SpecialFolders("Programs")
        shortcut_path = os.path.join(start_menu, self.display_name) + '.lnk'
        if os.path.exists(shortcut_path):
            os.unlink(shortcut_path)
        else:
            print(f"{shortcut_path} does not exist, nothing to delete")

    def install_dot_desktop_file(self):
        """Create a .desktop file for the launcher in the system applications menus.
        Linux only."""
        raise NotImplementedError

    def uninstall_dot_desktop_file(self):
        raise NotImplementedError


def set_window_appusermodel_id(module_name, window_id):
    """Set the Windows AppUserModelID settings for the given `window_id` to the appid
    for the given module based on its winlauncher configuration. If `window_id` is None
    or we are not on Windows, this will do nothing."""
    if window_id is not None and os.name == 'nt':
        _Module.instance(module_name).set_window_appusermodel_id(window_id)

def install(module_name):
    """Add a shortcut to launch the app for the given module to the system menus, i.e
    the start menu on Windows, ~/.local/share/applications on Linux, and TODO on
    macOS"""
    raise NotImplementedError

def uninstall(module_name):
    """Remove the app shortcut for the given modul from the system menus, i.e the start
    menu on Windows, ~/.local/share/applications on Linux, and TODO on macOS"""
    raise NotImplementedError