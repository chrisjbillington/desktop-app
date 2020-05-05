import os
import importlib.util


def get_package_directory(module_name):
    """Return the path of the package directory that the given module is in."""
    base_module = module_name.split('.', 1)[0]
    spec = importlib.util.find_spec(base_module)
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(base_module)
    if not spec.parent:
        msg = f'{base_module} is not a package'
        raise ValueError(msg)
    return os.path.dirname(spec.origin)


_desktop_escapes = {' ': R'\s', '\n': R'\n', '\t': R'\t', '\\': R'\\'}

def desktop_escape(s):
    """Escape path for use in .desktop file"""
    for unescaped, escaped in _desktop_escapes.items():
        s = s.replace(unescaped, escaped)
    return s
