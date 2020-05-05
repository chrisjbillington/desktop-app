








def main():
    pass
    # import argparse

    # parser = argparse.ArgumentParser(
    #     description="""A launcher for running Python scripts/apps on Windows,
    #     potentially in conda environments. Run a child Python subprocess, passing it the
    #     given argument list. If the Python interpreter used to invoke this script is
    #     Python.exe, then it will be used to invoke the subprocess, but if it is
    #     Pythonw.exe, the child will instead be run with the corresponding Python.exe
    #     with a hidden console window. This prevents a number of issues with using
    #     Pythonw.exe, but without having to show a console window. If the Python
    #     interpreter is within a conda environment, then the child process's environment
    #     will be modified to have the effect of activating the environment. If this
    #     script is invoked as an entry_point of another package, it will inspect
    #     sys.argv[0] to find the name of the entry_point script. The basename of the
    #     script, (excluding a '.exe' suffix (or 'w.exe' if a gui_script) will be
    #     interpreted as a module name, and that module - or its __main__.py if it's a
    #     package - will be run. Note that a package's __init__.py will not be run first
    #     as is the case with `python -m package_name`. This is a performance optimisation
    #     to allow the program to say, display a splash screen as soon as possible during
    #     startup. If it is necessary for __init__.py to run, the application's
    #     __main__.py should import it. In this way, an application may define gui_scripts
    #     and console_scripts entry_points named <modulename> and <modulenamew> that point
    #     to winlauncher:main to create launcher scripts."""
    # )

    # parser.add_argument(
    #     'args',
    #     metavar='args',
    #     type=str,
    #     nargs=argparse.REMAINDER,
    #     help="""Arguments to pass to the child Python interpreter. In the simplest case
    #         this simply the path to a script to be run, but may be '-m module_name' or
    #         any other arguments accepted by the Python' command""",
    # )
    # args = parser.parse_args().args

    # sys.exit(launch(*args))

if __name__ == '__main__':
    main()
