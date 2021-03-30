import argparse
from .shell import install, uninstall


def main():
    parser = argparse.ArgumentParser(
        description="""Create (or remove) a Start menu shortcut (Windows) or .desktop
            file (Linux) to run the Python module of the given name. The package owning
            the module must have configured appropriate entry_points for the module, and
            either have a desktop-app.json specifying the location of the icon files to
            use, or must have the files in the default locations. See the main
            desktop-app documentation for details."""
    )

    parser.add_argument(
        action="store",
        choices=['install', 'uninstall'],
        dest="action",
        help="""Whether to create (install) a shortcut or .desktop file, or to delete
            (uninstall) an existing one.""",
    )
    parser.add_argument(
        '--path',
        action="store",
        default=None,
        help="""Directory to create/delete shortcut or .desktop file. If not given,
            defaults to the Start menu on Windows, and to ~/.local/share/applications on
            Linux.""",
    )

    parser.add_argument(
        '--no-fix-entry-points',
        dest='no_fix_entry_points',
        default=False,
        action='store_true',
        help="If set, entry points will not be fixed for conda-environments "
        "during the install action."
    )
    parser.add_argument(
        '-q',
        '--quiet',
        action="store_true",
        help="""Don't print the names of files created/deleted.""",
    )
    parser.add_argument(action="store", dest="module", nargs='+')

    args = parser.parse_args()
    if args.action == 'install':
        for module in args.module:
            install(module, path=args.path, verbose=not args.quiet,
                    no_fix_entry_points=args.no_fix_entry_points)
    if args.action == 'uninstall':
        for module in args.module:
            uninstall(module, path=args.path, verbose=not args.quiet)


if __name__ == '__main__':
    main()
