import os
from textwrap import dedent

def _desktop_escape(s):
    """Escape a filepath for use in a .desktop file"""
    escapes = {' ': R'\s', '\n': R'\n', '\t': R'\t', '\\': R'\\'}
    for unescaped, escaped in escapes.items():
        s = s.replace(unescaped, escaped)
    return s

def get_user_applications():
    """Return the path to the user applications directory, where user .desktop files
    should be placed, typically ~/local/share/applications."""
    return os.path.join(
        os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share")), 'applications'
    )

def create_desktop_file(
    path, target, display_name, icon_file, overwrite=True
):
    if not overwrite and os.path.exists(path):
        raise FileExistsError(path)

    # TODO: customise declaring files accepted... %F arguments etc. Would require
    # additional config

    with open(path, 'w') as f:
        f.write(
            dedent(
                f"""\
            [Desktop Entry]
            Name={display_name}
            Exec={_desktop_escape(target)}
            Icon={_desktop_escape(icon_file)}
            Type=Application
            """
            )
        )
        