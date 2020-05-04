import sys
import os
from pathlib import Path
import sysconfig
import hashlib
import importlib.util
import json

CONFIG_FILENAME = 'winlauncher.json'


def _guess_currently_running_module():
    """Look in all parent directories of sys.argv[0] for a winlauncher.json config file,
    and return the closest parent module of sys.argv[0], if any."""
    script = Path(sys.argv[0]).absolute()
    parent = script.parent
    while parent.parent != parent:
        parent = parent.parent
        if os.path.exists(parent / CONFIG_FILENAME):
            with open(parent / CONFIG_FILENAME) as f:
                config = json.load(f)
                # Find the closest parent module, if any, of sys.argv[0]
                modules = sorted(
                    config['modules'],
                    key=lambda module: len(module.split('.')),
                    reverse=True,
                )
                for module in modules:
                    base, *sub_parts = module.split('.')
                    if base != parent.basename():
                        continue
                    module_path = Path(parent, *sub_parts)
                    if os.path.normcase(script).startswith(
                        os.path.normpath(module_path)
                    ):
                        return module
                msg = f"""Could not determine the current module: {script} is not a
                    submodule of any module in: {parent / CONFIG_FILENAME}."""
                raise LookupError(' '.join(msg.split()))
    msg = f"""Could not determine the current module: could not find a
        '{CONFIG_FILENAME}' in any parent directories of {script}"""
    raise LookupError(' '.join(msg.split()))


def _get_package_directory(module_name):
    """Return the path of the package directory that the given module is in."""
    base_module = module_name.split('.', 1)[0]
    spec = importlib.util.find_spec(base_module)
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(base_module)
    if not spec.parent:
        msg = f'{base_module} is not a package'
        raise ValueError(msg)
    return os.path.dirname(spec.origin)


class App:
    def __init__(self, module_name=None):
        """Object for managing shortcut creation and Windows AppUserModelID
        configuration for a a Python module configured to run as an app via winlauncher.
        If module_name is None, it will be guessed by looking in parent directories of
        `sys.argv[0]` until a 'winlauncher.json' config file is found, reading it, and
        seeing if sys.argv[0] is equal to or a submodule of one of the modules defined
        there.
        """
        if module_name is None:
            module_name = _guess_currently_running_module()
        self.module_name = module_name
        self.package_directory = _get_package_directory(module_name)
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
        appid for the module. If `window_id` is None or we are not on Windows, this
        method does nothing."""
        if window_id is None or not os.name == 'nt':
            return

        from win32com.propsys import propsys, pscon

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
        """Add a launcher for the module to the start menu."""
        from win32com.shell import shellcon
        from win32com.client import Dispatch
        from win32com.propsys import propsys, pscon

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


def _find_conda_env():
    """inspect whether sys.executable is within a conda environment and if it is, return
    the environment name and prefix. Otherwise return None, None"""
    prefix = os.path.dirname(sys.executable)
    if not os.path.isdir(os.path.join(prefix, 'conda-meta')):
        # Not a conda env
        return None, None
    if os.path.isdir(os.path.join(prefix, 'condabin')):
        # It's the base conda env:
        return 'base', prefix
    # Not the base env: its name is the directory basename:
    return os.path.basename(prefix), prefix


def _activate_conda_env(name, prefix):
    """Modify environment variables so as to effectively activate the given conda env
    from the perspective of child processes. If the conda env appears to already be
    active, do nothing. Does not set environment variables, instead returns a copy that
    may be passed to subprocess.Popen as the env arg."""
    env = os.environ.copy()
    if env['CONDA_DEFAULT_ENV'] == name and env['CONDA_PREFIX'] == prefix:
        # Env is already active
        return
    env['CONDA_DEFAULT_ENV'] = name
    env['CONDA_PREFIX'] = prefix
    #TODO: unix - compare $PATH before and after activating an env
    new_paths = os.path.pathsep.join(
        [
            prefix,
            os.path.join(prefix, "Library", "mingw-w64", "bin"),
            os.path.join(prefix, "Library", "usr", "bin"),
            os.path.join(prefix, "Library", "bin"),
            os.path.join(prefix, "Scripts"),
        ]
    )
    existing_paths = env.get('PATH', '')
    # Avoid a leading path separator in the PATH variable:
    if existing_paths:
        env['PATH'] = new_paths + os.path.pathsep + existing_paths
    else:
        env['PATH'] = new_paths

    return env


def launch(*args):
    """Runs a child Python subprocess, passing it the given argument list. If
    sys.executable is pythonw.exe, then the child process will be run with the
    corresponding python.exe with a hidden console window. Otherwise it will be run with
    sys.executable. If sys.executable is within a conda environment, then the child
    process's environment will be modified to have the effect of activating the
    environment."""
    import subprocess

    CREATE_NO_WINDOW = 1 << 27  # TODO: can use subprocess.CREATE_NO_WINDOW in py3.7+

    popen_kwargs = {}

    # TODO: virtualenv

    envname, prefix = _find_conda_env()
    if envname is not None:
        env = _activate_conda_env(envname, prefix)
        popen_kwargs['env'] = env

    python = sys.executable
    if os.path.basename(python).lower() == 'pythonw.exe':
        python = os.path.join(os.path.dirname(python), 'python.exe')
        popen_kwargs['creationflags'] = CREATE_NO_WINDOW

    return subprocess.call([python] + list(args), **popen_kwargs)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="""A launcher for running Python
        scripts/apps on Windows, potentially in conda environments. Run a child Python
        subprocess, passing it the given argument list. If the Python interpreter used
        to invoke this script is Python.exe, then it will be used to invoke the
        subprocess, but if it is Pythonw.exe, the child will instead be run with the
        corresponding Python.exe with a hidden console window. This prevents a number of
        issues with using Pythonw.exe, but without having to show a console window. If
        the Python interpreter is within a conda environment, then the child process's
        environment will be modified to have the effect of activating the environment.
        If this script is invoked as an entry_point of another package, it will inspect
        sys.argv[0] to find the name of the entry_point script. The basename of the
        script, (excluding a '.exe' suffix (or 'w.exe' if a gui_script) will be
        interpreted as a module name, and that module - or its __main__.py if it's a
        package - will be run. Note that a package's __init__.py will not be run first
        as is the case with `python -m package_name`. This is a performance optimisation
        to allow the program to say, display a splash screen as soon as possible during
        startup. If it is necessary for __init__.py to run, the application's
        __main__.py should import it. In this way, an application may define gui_scripts
        and console_scripts entry_points named <modulename> and <modulenamew> that point
        to winlauncher:main to create launcher scripts."""
    )

    parser.add_argument(
        'args',
        metavar='args',
        type=str,
        nargs=argparse.REMAINDER,
        help="""Arguments to pass to the child Python interpreter. In the simplest case
            this simply the path to a script to be run, but may be '-m module_name' or
            any other arguments accepted by the Python' command""",
    )
    args = parser.parse_args().args
    if os.path.abspath(__file__) != os.path.abspath(sys.argv[0]):
        # we're being run as an entry_point for an application. Insert that
        # application's main script at the start of the argument list.
        module_name = os.path.basename(sys.argv[0]).lower()
        if os.path.basename(sys.executable).lower() == 'pythonw.exe':
            module_name = module_name.rsplit('w', 1)[0]
        # Find the path of the module:
        package_directory = _get_package_directory(module_name)
        script_path = os.path.join(package_directory, *module_name.split('.')[1:])
        if os.path.isdir(script_path):
            script_path = os.path.join(script_path, '__main__.py')
        # Insert at the start of the argument list:
        args = [script_path] + args

    sys.exit(launch(*args))


if __name__ == '__main__':
    main()
