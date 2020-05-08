import sys
import os
import subprocess
from pathlib import Path

from .environment import (
    detect_conda_env,
    activate_conda_env,
    detect_venv,
    activate_venv,
    get_package_directory,
)


def entry_point():
    """Run a child Python process, passing it `[<script>] + sys.argv[1:]` as arguments.
    When complete, `sys.exit()` with its return code.

    `<script>` is determined from `sys.argv[0]`, which is assumed to be an
    `entry_points` script named as a dotted module path. A suffix '-gui', if present, is
    stripped from `sys.argv[0]` before treating it as a module name. `<script>` is set
    to the filepath of that module, or its `__main__.py` if it is a package.

    If `sys.executable` is Pythonw.exe, the subprocess is run with the corresponding
    Python.exe, but with `creationflags` set to `CREATE_NO_WINDOW` such that the process
    is started with a hidden console window. Otherwise the subprocess is run with
    `sys.executable`.

    If `sys.executable` appears to be within a conda or virtualenv environment, then the
    environment variables of the child process will be modified such that the
    environment is effectively activated for the subprocess. In this way an
    `entry_points` script may be run directly (such as from a start menu shortcut)
    without activating the virtual environment it is contained within, and the child
    process will still see an activated environment.

    Note that the path to the module is passed directly to Python as a script. This
    differs to running `python -m <modulename>` in that if the module is a package, its
    `__init__.py` will not be run first. This is something of an optimisation to allow
    GUI programs to display a splash screen before doing any other imports. If important
    initialisation is done in `__init__`, then the script should import the main package
    before such initialisation is required.
    """
    module_name, *_ = Path(sys.argv[0]).resolve().name.rsplit('-gui', 1)
    # Find the path of the module:
    package_directory = get_package_directory(module_name)
    script_path = os.path.join(package_directory, *module_name.split('.')[1:])
    if os.path.isdir(script_path):
        script_path = os.path.join(script_path, '__main__.py')

    popen_kwargs = {}

    conda_envname, conda_prefix = detect_conda_env()
    if conda_envname is not None:
        env = activate_conda_env(conda_envname, conda_prefix)
        popen_kwargs['env'] = env

    venv_prefix = detect_venv()
    if venv_prefix is not None:
        env = activate_venv(venv_prefix)
        popen_kwargs['env'] = env

    python = sys.executable
    if os.path.basename(python).lower() == 'pythonw.exe':
        python = os.path.join(os.path.dirname(python), 'python.exe')
        # TODO: can use subprocess.CREATE_NO_WINDOW once Python 3.6 is end-of-life
        CREATE_NO_WINDOW = 1 << 27
        popen_kwargs['creationflags'] = CREATE_NO_WINDOW

    try:
        sys.exit(subprocess.call([python, script_path] + sys.argv[1:], **popen_kwargs))
    except KeyboardInterrupt:
        sys.exit(1)
