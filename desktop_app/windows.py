import site
from pathlib import Path
from subprocess import list2cmdline, call, Popen, PIPE, DEVNULL
from .environment import WINDOWS


if WINDOWS:
    # Allow importing this module on other platforms even though the functions will fail
    from win32com.shell import shell, shellcon
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon
    from .wineventhook import sethook


def _checkwindows():
    if not WINDOWS:
        msg = "Windows-only function called on a non-Windows OS"
        raise EnvironmentError(msg)


def get_start_menu():
    """Return the path for Start menu entries for user-installed programs"""
    _checkwindows()
    return Path(Dispatch('WScript.Shell').SpecialFolders("Programs"))


def unredirect_appdata(path):
    """Copy a file within the appdata directory, that is actually in a local private
    copy of said directory, into the regular, shared-by-all-apps appdata directory.
    Delete the original file (but not necessarily parent directories). This is necessary
    if running on Python from the Windows Store, since Python.exe sees a private copy of
    appdata."""
    # The way this hack works is that we look site site.USER_BASE. This is the only clue
    # we have that our appdata is being redirected, since if it is, site.USER_BASE will
    # be in the redirected location. So that's how we get our hands on the path (this
    # ultimately came into the Python interpreter via an environment variable). Then we
    # launch non-python subprocesses to do the file copying for us, since the
    # subprocesses aren't subject to the redirect.
    real_path = Path(path)
    real_appdata = Path(Dispatch('WScript.Shell').SpecialFolders("AppData"))
    sandbox_appdata = Path(site.USER_BASE).parent / real_appdata.name
    sandbox_path = sandbox_appdata / real_path.relative_to(real_appdata)
    if sandbox_path.exists():
        # Yep, the file was redirected to the private copy of appdata:
        call(
            ['cmd.exe', '/c', 'mkdir', str(real_path.parent)],
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        proc = Popen(
            ['xcopy', str(sandbox_path), str(real_path), '/Y'],
            stdin=PIPE,
            stdout=DEVNULL,
            stderr=DEVNULL,
        )
        proc.communicate(b'F')  # This is so dumb
        sandbox_path.unlink()


def create_shortcut(
    shortcut_path,
    target,
    arguments=(),
    working_directory=None,
    icon_file=None,
    display_name=None,
    appusermodel_id=None,
):
    """Create a Windows shortcut at the given path, which should be a filepath ending in
    '.lnk'. Arguments should be a list or tuple of arguments - not a single string of
    arguments separated by spaces."""
    shortcut_path = Path(shortcut_path)
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    _checkwindows()
    objShell = Dispatch('WScript.Shell')
    shortcut = objShell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(target)
    if arguments:
        shortcut.Arguments = list2cmdline(arguments)
    if working_directory is not None:
        shortcut.WorkingDirectory = str(working_directory)
    if icon_file is not None:
        shortcut.IconLocation = str(icon_file)
    if display_name is not None:
        shortcut.Description = display_name
    shortcut.save()

    if appusermodel_id is not None:
        # Edit the shortcut to associate the AppUserModel_ID with it:
        store = propsys.SHGetPropertyStoreFromParsingName(
            str(shortcut_path), None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
        )
        store.SetValue(
            pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(appusermodel_id)
        )
        store.Commit()


def refresh_shell_cache():
    # Refresh the icon cache:
    shell.SHChangeNotify(
        shellcon.SHCNE_ASSOCCHANGED,
        shellcon.SHCNF_IDLIST | shellcon.SHCNF_FLUSH,
        None,
        None,
    )


def set_process_appusermodel_id(appid):
    _checkwindows()
    # shell.SetCurrentProcessExplicitAppUserModelID(appid)
    if not isinstance(appid, str) or len(appid) >= 1024:
        raise TypeError('appid must be a str of len < 1024')
    sethook(appid)
