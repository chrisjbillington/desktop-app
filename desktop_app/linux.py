import os
from textwrap import dedent
from pathlib import Path


def _desktop_escape(s):
    """Escape a filepath for use in a .desktop file"""
    escapes = {' ': R'\s', '\n': R'\n', '\t': R'\t', '\\': R'\\'}
    s = str(s)
    for unescaped, escaped in escapes.items():
        s = s.replace(unescaped, escaped)
    return s


def get_user_applications():
    """Return the path to the user applications directory, where user .desktop files
    should be placed, typically ~/local/share/applications."""
    data_home = os.getenv('XDG_DATA_HOME')
    if data_home is not None:
        data_home = Path(data_home)
    else:
        data_home = Path("~/.local/share").expanduser()
    return data_home / 'applications'


def create_desktop_file(path, target, display_name, icon_file, overwrite=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.exists():
        raise FileExistsError(path)

    # TODO: customise declaring files accepted... %F arguments etc. Would require
    # additional config

    contents = f"""\
            [Desktop Entry]
            Name={display_name}
            Exec={_desktop_escape(target)}
            Icon={_desktop_escape(icon_file)}
            Type=Application
            """
    path.write_text(dedent(contents), encoding='utf8')
