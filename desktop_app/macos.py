import plistlib
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


ICONSET_ENTRIES = [
    (16, ""),
    (16, "@2x"),
    (32, ""),
    (32, "@2x"),
    (128, ""),
    (128, "@2x"),
    (256, ""),
    (256, "@2x"),
    (512, ""),
    (512, "@2x"),
]


def get_user_applications():
    """Return the path to the per-user Applications directory."""
    return Path("~/Applications").expanduser()


def create_app_bundle(
    path,
    target,
    display_name,
    executable_name,
    bundle_identifier,
    icon_file=None,
    verbose=False,
):
    """Create a macOS .app bundle that launches target."""
    path = Path(path)
    contents = path / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)

    executable_path = macos / executable_name
    executable_path.write_text(
        "#!/bin/sh\n"
        'cd "$HOME"\n'
        f"exec {shlex.quote(str(target))} \"$@\"\n",
        encoding="utf8",
    )
    executable_path.chmod(executable_path.stat().st_mode | 0o755)

    plist = {
        "CFBundleExecutable": executable_name,
        "CFBundleIdentifier": bundle_identifier,
        "CFBundleName": display_name,
        "CFBundleDisplayName": display_name,
        "CFBundlePackageType": "APPL",
        "CFBundleInfoDictionaryVersion": "6.0",
    }
    icon_path = _create_icns(resources, icon_file, executable_name, verbose)
    if icon_path is not None:
        plist["CFBundleIconFile"] = icon_path.name

    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump(plist, f)
    (contents / "PkgInfo").write_text("APPL????", encoding="ascii")


def _create_icns(resources, icon_file, name, verbose):
    if icon_file is None:
        return None
    icon_file = Path(icon_file)
    if not icon_file.exists():
        return None

    output = resources / f"{name}.icns"
    if icon_file.suffix.lower() == ".icns":
        output.write_bytes(icon_file.read_bytes())
        return output

    with tempfile.TemporaryDirectory() as tmpdir:
        iconset = Path(tmpdir) / f"{name}.iconset"
        iconset.mkdir()
        for size, scale_suffix in ICONSET_ENTRIES:
            pixels = size * (2 if scale_suffix else 1)
            png = iconset / f"icon_{size}x{size}{scale_suffix}.png"
            if not _render_png(icon_file, png, pixels):
                if verbose:
                    print(
                        f"warning: could not create app icon from {icon_file}",
                        file=sys.stderr,
                    )
                return None
        try:
            subprocess.check_call(
                ["iconutil", "--convert", "icns", "--output", str(output), str(iconset)]
            )
        except (OSError, subprocess.CalledProcessError) as e:
            if verbose:
                print(f"warning: could not create app icon: {e}", file=sys.stderr)
            return None
        if not _icns_has_expected_entries(output):
            if verbose:
                print(
                    f"warning: app icon is missing required resolutions: {output}",
                    file=sys.stderr,
                )
            return None
    return output


def _icns_has_expected_entries(icon_file):
    with tempfile.TemporaryDirectory() as tmpdir:
        iconset = Path(tmpdir) / "icon.iconset"
        try:
            subprocess.check_call(
                [
                    "iconutil",
                    "--convert",
                    "iconset",
                    "--output",
                    str(iconset),
                    str(icon_file),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            return False
        for size, scale_suffix in ICONSET_ENTRIES:
            icon = iconset / f"icon_{size}x{size}{scale_suffix}.png"
            if not icon.exists():
                return False
    return True


def _render_png(icon_file, output, pixels):
    command = [
        "sips",
        "-z",
        str(pixels),
        str(pixels),
        str(icon_file),
        "--out",
        str(output),
    ]
    try:
        subprocess.check_call(
            command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        pass

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.check_call(
                ["qlmanage", "-t", "-s", str(pixels), "-o", tmpdir, str(icon_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            return False
        thumbnails = list(Path(tmpdir).iterdir())
        if not thumbnails:
            return False
        shutil.copyfile(thumbnails[0], output)
    return True
