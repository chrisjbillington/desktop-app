import sys
import sysconfig
import hashlib
import json
from pathlib import Path

from .environment import (
    get_package_directory,
    WINDOWS,
    LINUX,
    MACOS,
    short_envname,
)
from .windows import (
    get_start_menu,
    create_shortcut,
    set_process_appusermodel_id,
)

from .linux import get_user_applications, create_desktop_file


CONFIG_FILENAME = 'desktop-app.json'


class _ModuleConfig:
    """Object holding desktop-app configuration for a module"""

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
        self.module_directory = Path(
            self.package_directory, *self.module_name.split('.')[1:]
        )

        config = self._load_config()

        self.org_name = config.get('org_name', None)
        self.product_name = config.get('product_name', None)
        module_config = config.get('modules', {}).get(module_name, {})

        self.display_name = module_config.get('display_name', module_name)
        env = short_envname()
        if env is not None:
            self.display_name += f' ({env})'

        winicon = module_config.get('winicon', None)
        if winicon is None:
            self.winicon = self.module_directory / f'{module_name}.ico'
        else:
            self.winicon = self.package_directory / winicon

        icon = module_config.get('icon', None)
        if icon is None:
            self.icon = self.module_directory / f'{module_name}.svg'
            if not self.icon.exists():
                self.icon = self.module_directory / f'{module_name}.png'
        else:
            self.icon = self.package_directory / icon

        self.launcher_script_path = self._get_launcher_script_path()
        self.appid = self._get_appid()

    def _load_config(self):
        """Load 'desktop-app.json' from the module package directory and return it. If
        it doesn't exist, return an empty dict."""
        try:
            return json.loads(
                (self.package_directory / CONFIG_FILENAME).read_text(encoding='utf8')
            )
        except FileNotFoundError:
            return {}

    def _get_launcher_script_path(self):
        """Get the path to the script for launching the app without a console. It is
        assumed to be called <module_name>-gui and be in the bin or Scripts directory of
        the current Python interpreter as returned by `sysconfig.get_path('scripts')`.
        As such it will not be correct when used with `pip install --user` or any other
        custom options to pip that modify the install prefix."""
        # Look up the path to the launcher:
        script_path = Path(sysconfig.get_path('scripts'), self.module_name).absolute()
        if WINDOWS:
            return Path(script_path.parent, script_path.name + '-gui')
        return script_path

    def _get_appid(self):
        """ Create a string identifying the application, for use in OS interfaces such
        as as a Windows AppUserModelID. on Windows we use:

        <OrgName>.<ProductName>.<ModuleName>.Python-<hexdigits>

        OrgName or ProductName are omitted if not present in the configuration. The
        last field contains a hash of the path to the Python interpreter for the module,
        ensuring the appid is unique to the Python environment. The first three fields
        are converted to CamelCase, periods replaced with hyphens and underscores
        removed.

        On Linux we use:

        <module_name>-<envname>

        where <envname> is the name of the conda or virtualenv environment. The env is
        omitted if it's a conda env called 'base' or a virtualenv called '.venv' or
        'venv'. The reason we use a different format to Windows is that this will be
        used as the executable name of the app's process (sys.argv[0]), and so it's
        slightly more important for it to be user-friendly as it will appear as the
        default window title in some GUI toolkits.

        On macos it's the same as Linux, but this is likely to change when proper macos
        support is introduced.

        """
        # Hash the path to the Python interpreter directory so that we can include in
        # the appid a segment unique to the Python environment. .resolve() on the path
        # is important as it gets the correct case of the path - I've observed that in a
        # virtualenv sys.executable is all lower case. Using the directory instead of
        # the interpreter itself is important so that the hash is the same regardless of
        # whether python or pythonw is in use.

        if WINDOWS:
            replacements = {' ': '', '_': '', '.': '-'}
            interpreter_dir = Path(sys.executable).resolve().parent
            interpreter_hash = hashlib.sha256(bytes(interpreter_dir)).hexdigest()[:16]
            appid_parts = []
            for part in [self.org_name, self.product_name, self.module_name]:
                if part is None:
                    continue
                camelcase_part = part.title()
                for a, b in replacements.items():
                    camelcase_part = camelcase_part.replace(a, b)
                appid_parts.append(camelcase_part)
            appid_parts.append(f'Python-{interpreter_hash}')
            return '.'.join(appid_parts)
        else:  # TODO: consider macos
            env = short_envname()
            if env is None:
                return self.module_name
            return f'{self.module_name}-{env}'


def set_process_appid(module_name):
    """Associate the currently running process with the shortcut for the given module
    name. This should ensure the app has the correct icon in the taskbar, groups its
    windows correctly, can be pinned etc."""
    config = _ModuleConfig.instance(module_name)
    if WINDOWS:
        sys.argv[0] = str(config.launcher_script_path)
        set_process_appusermodel_id(config.appid)
    else:
        # Most Linux GUI toolkits set the X WM_CLASS property from the basename of
        # sys.argv[0], so ensuring it matches the name of our .desktop file is
        # sufficient to get DEs to correctly identify our app windows. Hopefully the
        # toolkits do the equivalent in Wayland - setting the app_id xdg-shell property.
        # If not, the user will need to make the right function call depending on their
        # GUI toolkit. Notable exception: tk doesn't use sys.argv[0] - the user needs to
        # set the tk classname to sys.argv[0] themselves.
        symlink_path = _launcher_script_symlink_path(config)
        if symlink_path is not None:
            sys.argv[0] = str(symlink_path)
        else:
            sys.argv[0] = str(config.launcher_script_path)
    # TODO: consider macos


def _default_shortcut_dir(config):
    if WINDOWS:
        path = get_start_menu()
        if config.org_name is not None:
            path /= config.org_name
        if config.product_name is not None:
            path /= config.product_name
        return path
    elif LINUX:
        return get_user_applications()
    elif MACOS:
        raise NotImplementedError


def _shortcut_name(config):
    if WINDOWS:
        return f'{config.display_name}.lnk'
    elif LINUX:
        return f'{config.appid}.desktop'
    elif MACOS:
        raise NotImplementedError


def _launcher_script_symlink_path(config):
    if not WINDOWS and config.appid != config.module_name:
        return config.launcher_script_path.parent / config.appid


def install(module_name, path=None, verbose=False):
    """Add a shortcut to launch the app for the given module to the system menus, i.e
    the start menu on Windows, ~/.local/share/applications on Linux, and TODO on macOS.
    If path is given, the shortcut will be created in the given directory instead. On
    Linux, in order to ensure the name of the shortcut (which may contain the name of a
    conda or virtualenv environment) matches the name of the executable it points to, a
    symbolic link called `<module_name>-<envname>` will be created."""
    config = _ModuleConfig.instance(module_name)
    if path is not None:
        path = Path(path)
    else:
        path = _default_shortcut_dir(config)
    shortcut_path = path / _shortcut_name(config)
    if shortcut_path.exists():
        if verbose:
            msg = f'warning: overwriting existing file {shortcut_path}'
            print(msg, file=sys.stderr)
        shortcut_path.unlink()
    if WINDOWS:
        create_shortcut(
            shortcut_path,
            config.launcher_script_path,
            working_directory=Path.home(),
            icon_file=config.winicon,
            display_name=config.display_name,
            appusermodel_id=config.appid,
        )
        if verbose:
            print(f' -> created {shortcut_path}')
    elif LINUX:
        symlink_path = _launcher_script_symlink_path(config)
        create_desktop_file(
            shortcut_path,
            target=symlink_path or config.launcher_script_path,
            display_name=config.display_name,
            icon_file=config.icon,
        )
        if verbose:
            print(f' -> created {shortcut_path}')
        if symlink_path is not None:
            if symlink_path.exists():
                if verbose:
                    msg = f'warning: overwriting existing symlink {symlink_path}'
                    print(msg, file=sys.stderr)
                    symlink_path.unlink()
            symlink_path.symlink_to(config.launcher_script_path)
            if verbose:
                print(
                    f' -> created symlink {symlink_path} -> '
                    + f'{config.launcher_script_path.name}'
                )
    elif MACOS:
        raise NotImplementedError


def uninstall(module_name, path=None, verbose=False):
    """Remove the app shortcut for the given module from the system menus, i.e the start
    menu on Windows, ~/.local/share/applications on Linux, and TODO on macOS. If a
    symlink was created within the scripts folder in install(), delete it."""
    config = _ModuleConfig.instance(module_name)
    if path is not None:
        path = Path(path)
    else:
        path = _default_shortcut_dir(config)
    files_to_delete = [path / _shortcut_name(config)]
    symlink_path = _launcher_script_symlink_path(config)
    if symlink_path is not None:
        files_to_delete.append(symlink_path)
    for file in files_to_delete:
        try:
            file.unlink()
            if verbose:
                print(f' -> deleted {file}')
        except FileNotFoundError:
            if verbose:
                print(f'warning: no such file {file}', file=sys.stderr)
