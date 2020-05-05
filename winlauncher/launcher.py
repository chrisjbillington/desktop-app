import sys
import os
import subprocess
from .utils import get_package_directory


def detect_conda_env():
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
    # TODO: unix - compare $PATH before and after activating an env
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


def detect_venv():
    raise NotImplementedError


def activate_venv():
    raise NotImplementedError


def entry_point():
    """Run a child Python process, passing it `[<script>] + sys.argv[1:]` as arguments.
    When complete, `sys.exit()` with its return code.

    `<script>` is determined from `sys.argv[0]`, which is assumed to be an
    `entry_points` script named as a dotted module path. `<script>` is set to the
    filepath of that module, or its `__main__.py` if it is a package.

    If sys.executable is Pythonw.exe, then a trailing 'w' is stripped from `sys.argv[0]`
    before treating it as a module name. In this case, the subprocess is run with the
    corresponding Python.exe, but with `creationflags` set to `CREATE_NO_WINDOW` such
    that the process is started with a hidden console window. Otherwise the subprocess
    is run with `sys.executable`. 

    If `sys.executable` appears to be within a conda environment or venv, then the
    environment variables of the child process will be modified such that the
    environment is effectively activated for the subprocess. In this way an
    `entry_points` script may be run directly (such as from a start menu shortcut)
    without activating the virtual environment it is contained within, but the child
    process will still see an activated environment.

    Note that the path to the module is passed directly to Python as a script. This
    differs to running `python -m <modulename>` in that if the module is a package, its
    `__init__.py` will not be run first. This is something of an optimisation to allow
    GUI programs to display a splash screen before doing any other imports.
    """
    module_name = os.path.basename(sys.argv[0]).lower()
    if os.path.basename(sys.executable).lower() == 'pythonw.exe':
        module_name = module_name.rsplit('w', 1)[0]
    # Find the path of the module:
    package_directory = get_package_directory(module_name)
    script_path = os.path.join(package_directory, *module_name.split('.')[1:])
    if os.path.isdir(script_path):
        script_path = os.path.join(script_path, '__main__.py')

    CREATE_NO_WINDOW = 1 << 27  # TODO: can use subprocess.CREATE_NO_WINDOW in py3.7+

    popen_kwargs = {}

    # TODO: virtualenv

    envname, prefix = detect_conda_env()
    if envname is not None:
        env = activate_conda_env(envname, prefix)
        popen_kwargs['env'] = env

    python = sys.executable
    if os.path.basename(python).lower() == 'pythonw.exe':
        python = os.path.join(os.path.dirname(python), 'python.exe')
        popen_kwargs['creationflags'] = CREATE_NO_WINDOW

    try:
        sys.exit(subprocess.call([python, script_path] + sys.argv[1:], **popen_kwargs))
    except KeyboardInterrupt:
        sys.exit(1)
