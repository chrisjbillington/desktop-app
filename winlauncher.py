import sys
import os
from pathlib import Path
import sysconfig
import hashlib
import importlib.util


class App:
    def __init__(self, module_name):
        """Object for managing shortcut creation and Windows AppUserModelID
        configuration. `company_name` must be an organisation or company name in
        CamelCase. `product_name` is optional, it should be used if there are multiple
        applications under the same product umbrella, and it should also be in
        CamelCase. `launcher_name_suffix` is a suffix to be appended to the
        human-readable application launchers that will be created. If given, the
        launcher names with be of the format "<appname> - <suffix>" with a hyphen with
        spaces around it inserted."""
        self.company_name = company_name
        self.product_name = product_name
        self.launcher_name_suffix = launcher_name_suffix

    def get_package_directory(self, appname=None):
        """Return the path of the package directory for the given `appname`, assuming it
        corresponds to an importable package. If `appname` is not given, it will be as
        returned by `self.get_currently_running_appname()`"""
        spec = importlib.util.find_spec(appname)
        if spec is None or spec.origin is None:
            raise ModuleNotFoundError(appname)
        if not spec.parent:
            msg = f'{appname} is not a package'
            raise ValueError(msg)
        return os.path.dirname(spec.origin)

    def get_currently_running_appname(self):
        """Determine the currently running module name or package name from
        `sys.argv[0]` assuming that it is either to a toplevel module or the
        `__main__.py` of a package."""
        script = Path(sys.argv[0]).absolute()
        if script.stem == '__main__':
            return script.parent.stem
        else:
            return script.stem

    def get_script_path(self, appname=None):
        """Get the path to the script for launching the app. It is assumed to be called
        <appname> and be in the bin or Scripts directory of the current Python
        interpreter as returned by `sysconfig.get_path('scripts')`. As such it will not
        be correct when used with `pip install --user` or any other custom options to
        pip that modify the install prefix. If `appname` is not given, it will be as
        returned by `self.get_currently_running_appname()`."""
        if appname is None:
            appname = self.get_currently_running_appname()
        # Look up the path to the launcher:
        script_path = str(Path(sysconfig.get_path('scripts'), appname).absolute())
        if os.name == 'nt':
            return script_path + 'w.exe'
        return script_path

    def get_appid(self, appname=None):
        """ Create a string identifying the application, for use in OS interfaces such
        as as a Windows AppUserModelID. The required format of a windows AppUserModelID
        is:
        
        CompanyName.ProductName.SubProduct.VersionInformation
        
        Where the last two fields are optional. If `product_name` was passed to the
        contructor, then the format returned is:

        CompanyName.ProductName.<CamelCaseAppName>.Python-<hexdigits>

        otherwise ProductName will be ommited. The last field contains a hash of the
        path to the Python interpreter for the application, ensuring the appid is unique
        to the Python environment.
        """
        if appname is None:
            appname = self.get_currently_running_appname()

        # Hash the path to the Python interpreter so that we can include in the appid a
        # segment unique to the Python environment. Note the case-insensitivity - I've
        # observed the case differing depending on whether a virtualenv is active, so
        # better use normpath to not vary with changes in case:
        interpreter_hash = hashlib.sha256(
            os.fsencode(os.path.normcase(sys.executable))
        ).hexdigest()[:16]

        camelcase_appname = ''.join(s.capitalize() for s in appname.split('_'))
        appid_parts = [self.company_name]
        if self.product_name is not None:
            appid_parts.append(self.product_name)
        appid_parts.append(camelcase_appname)
        appid_parts.append('Python-' + interpreter_hash)
        return '.'.join(appid_parts)

    def get_launcher_name(self, appname=None):
        """Get a human readable name appropriate for naming the launcher. If `appname`
        is not given, it will be as returned by
        `self.get_currently_running_appname()`"""
        # TODO conda envs
        if appname is None:
            appname = self.get_currently_running_appname()
        if self.launcher_name_suffix is not None:
            return f'{appname} - {self.launcher_name_suffix}'
        return appname

    def get_icon_path(self, appname=None, extension='.ico'):
        """Return the path to the application .ico file if on Windows, or another format
        (such as .svg) if `extension` is given. It is assumed that these are named
        `<appname>.ico` or `<appname>.svg` and are directly within the `<appname>`
        package directory. If `appname` is not given, it will be as returned by
        `self.currently_running_appname()`"""
        if appname is None:
            appname = self.get_currently_running_appname
        return os.path.join(self.get_package_directory(appname), appname) + extension

    def set_window_appusermodel_id(self, window_id, appname=None):
        """Set the Windows AppUserModelID settings for the given `window_id` to those
        corresponding to the given `appname`. If `appname` is not given, it will be as
        returned by `self.currently_running_appname()`. If `window_id` is None or we are
        not on Windows, do nothing."""
        if window_id is None or not os.name == 'nt':
            return

        from win32com.propsys import propsys, pscon
        import pythoncom

        if appname is None:
            appname = self.get_currently_running_appname()

        store = propsys.SHGetPropertyStoreForWindow(
            window_id, propsys.IID_IPropertyStore
        )

        # AppUserModelID
        store.SetValue(
            pscon.PKEY_AppUserModel_ID,
            propsys.PROPVARIANTType(self.get_appid(appname), pythoncom.VT_LPWSTR),
        )

        # Relaunch command
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchCommand,
            propsys.PROPVARIANTType(self.get_script_path(appname), pythoncom.VT_LPWSTR),
        )

        # Launcher name
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchDisplayNameResource,
            propsys.PROPVARIANTType(
                self.get_launcher_name(appname), pythoncom.VT_LPWSTR
            ),
        )

        # Icon
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchIconResource,
            propsys.PROPVARIANTType(self.get_icon_path(appname), pythoncom.VT_LPWSTR),
        )

        store.Commit()

    def add_to_start_menu(self, appname=None):
        """Add a launcher for the given app to the start menu. If `appname` is not
        given, it will be as returned by `self.currently_running_appname()`."""
        from win32com.shell import shellcon
        from win32com.client import Dispatch
        from win32com.propsys import propsys, pscon
        import pythoncom

        objShell = Dispatch('WScript.Shell')
        start_menu = objShell.SpecialFolders("Programs")

        if appname is None:
            appname = self.get_currently_running_appname()

        launcher_name = self.get_launcher_name(appname)
        shortcut_path = os.path.join(start_menu, launcher_name) + '.lnk'

        # Overwrite previously existing shortcuts of the same name:
        if os.path.exists(shortcut_path):
            os.unlink(shortcut_path)

        shortcut = objShell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = self.get_script_path(appname)
        shortcut.WorkingDirectory = str(Path('~').expanduser)
        shortcut.IconLocation = self.get_icon_path(appname)
        shortcut.Description = launcher_name
        shortcut.save()

        # Edit the shortcut to associate the AppUserModel_ID with it:
        store = propsys.SHGetPropertyStoreFromParsingName(
            shortcut_path, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
        )
        store.SetValue(
            pscon.PKEY_AppUserModel_ID,
            propsys.PROPVARIANTType(self.get_appid(appname), pythoncom.VT_LPWSTR),
        )
        store.Commit()


def find_conda_env():
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


def activate_conda_env(name, prefix):
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

def run(*args):
    """Runs a child Python subprocess, passing it the given argument list. If
    sys.executable is pythonw.exe, then the child process will be run with the
    corresponding python.exe with a hidden console window. Otherwise it will be run with
    sys.executable. If sys.executable is within a conda environment, then the child
    process's environment will be modified to have the effect of activating the
    environment."""
    import subprocess

    CREATE_NO_WINDOW = 1 << 27 # TODO: can use subprocess.CREATE_NO_WINDOW in py3.7+

    popen_kwargs = {}

    envname, prefix = find_conda_env()
    if envname is not None:
        env = activate_conda_env(envname, prefix)
        popen_kwargs['env'] = env

    python = sys.executable
    if os.path.basename(python).lower() == 'pythonw.exe':
        python = os.path.join(os.path.dirname(python), 'python.exe')
        popen_kwargs['creationflags'] = CREATE_NO_WINDOW

    return subprocess.call([python] + list(args), **popen_kwargs)

def main():
    import argparse

    parser = argparse.ArgumentParser( description="""A launcher for running Python
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
        # Find the import path of the module:
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            raise ModuleNotFoundError(module_name)
        if spec.parent:
            # A package:
            script = os.path.join(os.path.dirname(spec.origin), '__main__.py')
        else:
            # A single-file module:
            script = spec.origin
        # Insert at the start of the argument list:
        args = [script] + args

    sys.exit(run(*args))

if __name__ == '__main__':
    main()
