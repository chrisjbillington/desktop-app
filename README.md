Winlaucher
==========

`winlauncher` simplifies making a Python GUI application launch and behave in a standard
way with respect to the Windows Start menu and taskbar.

If your application is a Python module runnable from the command line as `python -m
mymodule`, then with minimal configuration `winlauncher` can:

* Create a launcher `.exe` that runs your application
    * with a hidden console
    * after activating a `conda` environment or virtualenv, if any
* Create a start menu entry for your application (that runs said `.exe`)
* Ensure your application appears in the Windows taskbar with the correct name and icon,
  and can be pinned correctly.

Though most of the problems it solves are Windows-specific, `winlauncher` can be used
for cross platform apps. On all platforms it creates launcher scripts, though the hidden
console is only relevant to Windows.

* On Linux instead of start menu entries it will create a `.desktop` file for your
  application so that it appears in your desktop environment's application menus.

* It does not yet create an app launcher on MacOS, but it's on the TODO list.


Usage
=====


Details
=======

Hidden console
--------------
The usual recommendation to run Python GUI applications is with `Pythonw.exe`, which
does not create a console window. However, when running under `Pythonw.exe`, a simple
`print()` call will raise an exeption, and certain low-level output redirection of
subprocesses does not work due to the `stdout` and `stderr` filehandles not existing.

So that you don't have to worry about your application producing some output, and to
ensure output filehandles exist from the perspective of subprocesses, in Windows the
launcher script runs your application in a subprocess using `Python.exe`, but with the
`CREATE_NO_WINDOW` flag so that the console exists, but is not visible.

