desktop-app
==========

`desktop-app` simplifies making a Python GUI application install, launch, and behave in
a standard way with respect to the application menus and the taskbar in Windows and
Linux (Macos support planned).

If your application is a Python module runnable from the command line as `python -m
mymodule`, then with minimal configuration `desktop-app` can:

* Create a launcher script (or `.exe` on windows) that runs your application
    * after activating a `conda` env or virtual environment, if any
    * with a hidden console if on Windows
* Install a start menu shortcut (Windows) or `.desktop` file (Linux) to launch your
  application from your desktop applications menu
* Ensure your application appears in the taskbar with the correct name and icon,
  and can be pinned correctly.


Basic Usage
===========

Here we'll follow the example in this repository for a module called `oink`, developed
by Old MacDonald's Farm. Before Old MacDonald had heard of `desktop-app`, he had a
package that looked like this:
```
.
├── oink
│   ├── __init__.py
│   └── __main__.py
└── setup.py
```

Where `setup.py` is:
```python
from setuptools import setup

setup(
    name='oink',
    version='1.0',
    author='Old MacDonald',
    author_email="macdonald@eie.io",
    url='http://eie.io',
    packages=["oink"],
    setup_requires=['setuptools'],
)
```

`__main__.py` is:
```python
import tkinter

root = tkinter.Tk()
root.geometry("300x300")
w = tkinter.Label(root, text="Oink!")
w.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)
root.mainloop()
```

And `__init__.py` is empty.

After installing this package somewhere, MacDonald can run it from a terminal with
`python -m oink`, and it shows a little window


[README still in progress!]


Reasons
=======

Why a hidden console on Windows?
--------------------------------

The usual recommendation to run Python GUI applications is with `Pythonw.exe`, which
does not create a console window. However, when running under `Pythonw.exe`, a simple
`print()` call will raise an exception, and [certain low-level output
redirection](https://github.com/labscript-suite/lyse/issues/48#issuecomment-609371880)
of subprocesses does not work due to the `stdout` and `stderr` filehandles not existing.
Furthermore, some tools may create subprocesses that call `cmd.exe`, or `Python.exe`,
briefly popping up console windows of their own since one doesn't already exist.

In order to be able to ignore these problems and code the same as you would with a
console, in Windows the launcher script runs your application in a subprocess using
`Python.exe`, but with the `CREATE_NO_WINDOW` flag so that the console exists, but is
not visible.

Why activate environments?
--------------------------

Activating environments is not strictly necessary except when using conda on Windows, in
which case some compiled extensions (notably, Qt libraries) cannot be imported unless
the environment is active.

However, even on other platforms activating the environment simplifies running other
programs that might be installed to the `bin`/`Scripts` directory of the virtual
environment - calling code would otherwise have to manually find this directory and
provide the full path to the programs it wants to run.

