import sys
import os
import importlib.util
import platform
from functools import lru_cache

_os = platform.system()
WINDOWS = _os == 'Windows'
LINUX = _os == 'Linux'
MACOS = _os == 'Darwin'
if not (WINDOWS or LINUX or MACOS):
    raise EnvironmentError("Can't determine operating system")


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

@lru_cache
def detect_conda_env():
    """Inspect whether sys.executable is within a conda environment and if it is, return
    the environment name and prefix. Otherwise return None, None"""
    prefix = os.path.dirname(sys.executable)
    if not WINDOWS:
        # On unix, python is in <prefix>/bin, and in windows it's directly in <prefix>
        prefix = os.path.dirname(prefix)
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
    active, do nothing. Does not actually set environment variables, instead returns a
    copy that may be passed to subprocess.Popen as the env arg. Not all environment
    variables are considered, only CONDA_DEFAULT_ENV, CONDA_PREFIX, and PATH."""
    env = os.environ.copy()
    if (
        env.get('CONDA_DEFAULT_ENV', '') == name
        and os.path.normcase(env.get('CONDA_PREFIX', '')) == prefix
    ):
        # Env is already active
        return
    env['CONDA_DEFAULT_ENV'] = name
    env['CONDA_PREFIX'] = prefix
    if WINDOWS:
        env['PATH'] = os.path.pathsep.join(
            [
                prefix,
                os.path.join(prefix, "Library", "mingw-w64", "bin"),
                os.path.join(prefix, "Library", "usr", "bin"),
                os.path.join(prefix, "Library", "bin"),
                os.path.join(prefix, "Scripts"),
                env['PATH'],
            ]
        )
    else:
        env['PATH'] = os.path.pathsep.join([os.path.join(prefix, 'bin'), env['PATH']])

    return env

@lru_cache
def detect_venv():
    """Inspect whether sys.executable is within a virtualenv and if it is, return the
    virtualenv prefix. Otherwise return None"""
    if hasattr(sys, 'real_prefix'):
        # virtualenv < v20 sets sys.real_prefix, which doesn't exist otherwise
        return sys.prefix
    if sys.base_prefix != sys.prefix:
        # virtualenv >= v20 sets sys.base_prefix, which always exists
        return sys.prefix


def activate_venv(prefix):
    """Modify environment variables so as to effectively activate the given virtualenv
    from the perspective of child processes. If the virtualenv appears to already be
    active, do nothing. Does not actually set environment variables, instead returns a
    copy that may be passed to subprocess.Popen as the env arg."""

    env = os.environ.copy()
    if os.path.normcase(env.get('VIRTUAL_ENV', '')) == os.path.normcase(prefix):
        # Env is already active
        return
    env['VIRTUAL_ENV'] = prefix
    env.pop('PYTHONHOME', None)
    if WINDOWS:
        env['PATH'] = os.path.pathsep.join(
            [os.path.join(prefix, 'Scripts'), env['PATH']]
        )
    else:
        env['PATH'] = os.path.pathsep.join([os.path.join(prefix, 'bin'), env['PATH']])

    return env


def short_envname():
    """Get a short name useful for distinguishing an environment from other
    environments. For conda, it's the name of the env or None if it's the base env. For
    venv its the name of the venv directory with any leading '.' stripped off, or None
    if that results in 'venv'. It's also None if we're not in either kind of
    environment"""
    envname, _ = detect_conda_env()
    if envname is not None:
        if envname == 'base':
            return None
        return envname
    envpath = detect_venv()
    if envpath is not None:
        envname = os.path.basename(envpath).lstrip('.')
        if envname == 'venv':
            return None
        return envname
