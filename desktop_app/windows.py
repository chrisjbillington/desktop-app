from pathlib import Path
from subprocess import list2cmdline
from .environment import WINDOWS

if WINDOWS:
    # Allow importing this module on other platforms even though the functions will fail
    from win32com.shell import shell, shellcon
    from win32com.client import Dispatch
    from win32com.propsys import propsys, pscon


def _checkwindows():
    if not WINDOWS:
        msg = "Windows-only function called on a non-Windows OS"
        raise EnvironmentError(msg)


def get_start_menu():
    """Return the path for Start menu entries for user-installed programs"""
    _checkwindows()
    return Path(Dispatch('WScript.Shell').SpecialFolders("Programs"))


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

    # Refresh the icon cache:
    shell.SHChangeNotify(
        shellcon.SHCNE_ASSOCCHANGED,
        shellcon.SHCNF_IDLIST | shellcon.SHCNF_FLUSH,
        None,
        None,
    )

def set_process_appusermodel_id(appid):
    _checkwindows()
    shell.SetCurrentProcessExplicitAppUserModelID(appid)