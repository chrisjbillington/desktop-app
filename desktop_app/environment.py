import sys
import os
import site
import sysconfig
from importlib.util import find_spec
import platform
from functools import lru_cache
from pathlib import Path
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

_os = platform.system()
WINDOWS = _os == 'Windows'
LINUX = _os == 'Linux'
MACOS = _os == 'Darwin'
if not (WINDOWS or LINUX or MACOS):
    raise EnvironmentError("Can't determine operating system")


# Three possible locations for scripts.

# Main scripts dir for the Python environment:
PY_SCRIPTS = Path(sysconfig.get_path('scripts'))
# Used in Debian-based distros for packages installed with `sudo pip install`:
LOCAL_SCRIPTS = Path('/usr/local/bin')
# Packages installed to the user's home directory with `pip install --local`. Even if
# the user doesn't type `--local`, this option is enabled by default on Debian-based
# distros when running without sudo, and for the Python shipped in the Microsoft Store:
if WINDOWS:
    USER_SCRIPTS = Path(sysconfig.get_path('scripts', scheme='nt_user'))
else:
    USER_SCRIPTS = Path(sysconfig.get_path('scripts', scheme='posix_user'))

# Possible locations for installed packages:

# Arbitrary number of site packages directories:
def _site_packages():
    return [Path(s) for s in site.getsitepackages()]


# Only one user site packages directory:
def _user_site_packages():
    return Path(site.getusersitepackages())


def _reverse_egg_link_lookup(directory):
    # For packages 'installed' with `pip install -e`, the import path is the development
    # directory, which is not very useful in figuring out what the corresponding scripts
    # directory is. This function looks through canonical installation locations for
    # .egg-link files, and if any is found that points to the given directory, the
    # parent directory of the .egg-link file is returned. Otherwise returns None.
    directory = Path(directory).absolute()
    for sitedir in _site_packages() + [_user_site_packages()]:
        if not sitedir.is_dir():
            continue
        sitedir = Path(sitedir).absolute()
        if sitedir.exists and sitedir.is_dir:
            for file in sitedir.iterdir():
                if file.suffix == '.egg-link':
                    # The first line is the path to the .egg:
                    linkpath = Path(file.read_text("utf8").splitlines()[0])
                    # is allowed to be relative to the containing dir:
                    linkpath = Path(sitedir, linkpath)
                    if linkpath == directory.parent:
                        return sitedir

    # For new PEP660-style editable installs, we instead look a) through sys.modules for
    # modules with names starting with '__editable__', and inspect their MAPPING
    # attribute, and b) through site_packages for __editable__*.pth files specifying a
    # simple
    for name, module in sys.modules.items():
        if name.startswith('__editable__'):
            if directory in [Path(s) for s in module.MAPPING.values()]:
                return Path(module.__file__).parent

    # And now for src-layout packages.

    # Bit of duplication here with the above code for .egg-link files. Prefer this to
    # keep it separate.
    for sitedir in _site_packages() + [_user_site_packages()]:
        if not sitedir.is_dir():
            continue
        sitedir = Path(sitedir).absolute()
        if sitedir.exists and sitedir.is_dir:
            for file in sitedir.iterdir():
                if file.name.startswith('__editable__') and file.suffix == '.pth':
                    contents = file.read_text("utf8")
                    if contents.startswith("import"):
                        # This one's a dynamic loader, skip it.
                        continue
                    # The first line is the path to the .egg:
                    linkpath = contents.strip()
                    # is allowed to be relative to the containing dir:
                    linkpath = Path(sitedir, linkpath)
                    if linkpath == directory.parent:
                        return sitedir


def get_install_directory(module_name):
    """Return the installation directory of the module - an entry in the list of site
    packages directories, or the user site packages directory."""
    import_path = get_package_directory(module_name)
    for sitedir in _site_packages() + [_user_site_packages()]:
        if sitedir in import_path.parents:
            return sitedir
    # May return None if there is no egg-link to the package directory either
    return _reverse_egg_link_lookup(import_path)


def get_scripts_dir(module_name):
    """Return the directory of the scripts installed with the package supplying the
    given module. If the package is not installed, returns None."""
    install_dir = get_install_directory(module_name)
    if install_dir is not None:
        if Path('/usr/local') in install_dir.parents:
            return LOCAL_SCRIPTS
        elif install_dir in _site_packages():
            return PY_SCRIPTS
        elif install_dir == _user_site_packages():
            return USER_SCRIPTS


def get_package_directory(module_name):
    """Return Path of the package directory that the given module is in."""
    base_module = module_name.split('.', 1)[0]
    spec = find_spec(base_module)
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(base_module)
    if not spec.parent:
        msg = f'{base_module} is not a package'
        raise ValueError(msg)
    return Path(spec.origin).parent


def get_distribution_of_module(module_name):
    """Return the name of the distribution providing the given module"""
    base_module = module_name.split('.', 1)[0]
    for distribution in importlib_metadata.distributions():
        if distribution.files is None:
            continue
        for path in distribution.files:
            if Path(path).parts[0] == base_module:
                return distribution.metadata['Name']


@lru_cache()
def detect_conda_env():
    """Inspect whether `sys.executable` is within a conda environment and if it is,
    return the environment name and Path of its prefix. Otherwise return None, None"""
    prefix = Path(sys.prefix)
    if not (prefix / 'conda-meta').is_dir():
        # Not a conda env
        return None, None
    if (prefix / 'envs').is_dir():
        # It's the base conda env:
        return 'base', prefix
    # Not the base env: its name is the directory basename:
    return prefix.name, prefix


def activate_conda_env(name, prefix):
    """Modify environment variables so as to effectively activate the given conda env
    from the perspective of child processes. If the conda env appears to already be
    active, do nothing. Does not actually set environment variables, instead returns a
    copy that may be passed to subprocess.Popen as the env arg. Not all environment
    variables are considered, only CONDA_DEFAULT_ENV, CONDA_PREFIX, and PATH."""
    prefix = Path(prefix)
    env = os.environ.copy()
    current_name = env.get('CONDA_DEFAULT_ENV')
    current_prefix = env.get('CONDA_PREFIX')
    if current_prefix is not None:
        current_prefix = Path(current_prefix)
    if current_name == name and current_prefix == prefix:
        # Env is already active
        return
    env['CONDA_DEFAULT_ENV'] = name
    env['CONDA_PREFIX'] = str(prefix)
    if WINDOWS:
        env['PATH'] = os.path.pathsep.join(
            [
                str(prefix),
                str(prefix / "Library" / "mingw-w64" / "bin"),
                str(prefix / "Library" / "usr" / "bin"),
                str(prefix / "Library" / "bin"),
                str(prefix / "Scripts"),
                env['PATH'],
            ]
        )
    else:
        env['PATH'] = os.path.pathsep.join([str(prefix / 'bin'), env['PATH']])

    return env


@lru_cache()
def detect_venv():
    """Inspect whether sys.executable is within a virtual environment and if it is,
    return the virtual environment Path of prefix. Otherwise return None"""
    if hasattr(sys, 'real_prefix'):
        # virtualenv < v20 sets sys.real_prefix, which doesn't exist otherwise
        return Path(sys.prefix)
    if sys.base_prefix != sys.prefix:
        # virtualenv >= v20 sets sys.base_prefix, which always exists
        return Path(sys.prefix)


def activate_venv(prefix):
    """Modify environment variables so as to effectively activate the given virtual
    environment from the perspective of child processes. If the virtual environment
    appears to already be active, do nothing. Does not actually set environment
    variables, instead returns a copy that may be passed to subprocess.Popen as the env
    arg."""
    prefix = Path(prefix)
    env = os.environ.copy()
    current_env = env.get('VIRTUAL_ENV')
    if current_env is not None:
        current_env = Path(current_env)
    if current_env == prefix:
        # Env is already active
        return
    env['VIRTUAL_ENV'] = str(prefix)
    env.pop('PYTHONHOME', None)
    if WINDOWS:
        env['PATH'] = os.pathsep.join([str(prefix / 'Scripts'), env['PATH']])
    else:
        env['PATH'] = os.pathsep.join([str(prefix / 'bin'), env['PATH']])
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
        envname = envpath.name.lstrip('.')
        if envname == 'venv':
            return None
        return envname

def get_venv_executable_and_env(env=None):
    """If we are running in a venv on Windows or MacOS such that sys.executable is a
    shim to sys._base_executable, then return sys._base_executable, as well as the
    environment that should be passed to sys._base_executable in order for it to know to
    configure itself for the virtual environment instead of the base environment. This
    allows us to skip the shim and thus have fewer layers in our process hierarchy. If
    we are not in a venv, return sys.executable and the env as passed in. If env passed
    in is None, and needs to be modified for the subprocess, a copy of os.environ(),
    appropriately modified, will be returned."""
    base_executable = getattr(sys, '_base_executable', sys.executable)
    if Path(base_executable) != Path(sys.executable):
        if env is None:
            env = os.environ.copy()
        env["__PYVENV_LAUNCHER__"] = str(sys.executable)
        return base_executable, env
    return sys.executable, env

