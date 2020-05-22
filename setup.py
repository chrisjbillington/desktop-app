import os
from setuptools import setup, Extension
import platform

VERSION_SCHEME = {
    "version_scheme": os.getenv("SCM_VERSION_SCHEME", "guess-next-dev"),
    "local_scheme": os.getenv("SCM_LOCAL_SCHEME", "node-and-date"),
}

# The extension still exists on unix, it's just an empty module. This ensures wheel
# knows it is an impure package.
WINDOWS = platform.system() == 'Windows'
EXT_MODULES = [
    Extension(
        'desktop_app.wineventhook',
        sources=[os.path.join('src', 'wineventhook.cpp')],
        libraries=["user32", "shell32", "ole32"] if WINDOWS else [],
    )
]

setup(
    use_scm_version=VERSION_SCHEME,
    ext_modules=EXT_MODULES,
)
