import os
from setuptools import setup, Extension
import platform

VERSION_SCHEME = {
    "version_scheme": os.getenv("SCM_VERSION_SCHEME", "guess-next-dev"),
    "local_scheme": os.getenv("SCM_LOCAL_SCHEME", "node-and-date"),
}

WINDOWS = platform.system() == 'Windows'

# The extension is still defined, but has no sources on Unix. This ensures wheel knows
# it is an impure package.
EXT_MODULES = [
    Extension(
        'desktop_app.wineventhook',
        sources=[os.path.join('src', 'wineventhook.cpp')] if WINDOWS else [],
        libraries=["user32", "shell32", "ole32"] if WINDOWS else [],
    )
]

setup(
    use_scm_version=VERSION_SCHEME,
    ext_modules=EXT_MODULES,
)
