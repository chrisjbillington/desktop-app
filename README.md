desktop-app
==========

`desktop-app` simplifies making a Python GUI application install, launch, and behave in
a standard way with respect to the application menus and the taskbar in Windows and
Linux (Macos support planned).

If your application is a Python module runnable from the command line as `python -m
mymodule`, then with minimal configuration `desktop-app` can:

* Create a launcher `.exe` that runs your application
    * after activating a `conda` environment or virtualenv, if any
    * with a hidden console if on Windows
* Create a start menu shortcut (Windows) or `.desktop` file (Linux) to launch your
  application from your desktop applications menu
* Ensure your application appears in the taskbar with the correct name and icon,
  and can be pinned correctly.


Usage
=====


Details
=======

Hidden console on Windows
-------------------------

The usual recommendation to run Python GUI applications is with `Pythonw.exe`, which
does not create a console window. However, when running under `Pythonw.exe`, a simple
`print()` call will raise an exeption, and certain low-level output redirection of
subprocesses does not work due to the `stdout` and `stderr` filehandles not existing.

So that you don't have to worry about your application producing some output, and to
ensure output filehandles exist from the perspective of subprocesses, in Windows the
launcher script runs your application in a subprocess using `Python.exe`, but with the
`CREATE_NO_WINDOW` flag so that the console exists, but is not visible.


Limitations
-----------

No pip install --user because we can't work out where the scripts directory is