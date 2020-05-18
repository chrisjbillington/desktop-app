import os
from setuptools import setup, Extension
import platform

try:
    from setuptools_conda import dist_conda
    CMDCLASS = {"dist_conda": dist_conda}
except ImportError:
    CMDCLASS = {}

VERSION_SCHEME = {
    "version_scheme": os.getenv("SCM_VERSION_SCHEME", "guess-next-dev"),
    "local_scheme": os.getenv("SCM_LOCAL_SCHEME", "node-and-date"),
}

if platform.system() == 'Windows':
    EXT_MODULES = [
        Extension(
            'desktop_app.wineventhook',
            sources=[os.path.join('src', 'wineventhook.cpp')],
            libraries=["user32", "shell32", "ole32"],
        )
    ]
else:
    EXT_MODULES = []

setup(
    use_scm_version=VERSION_SCHEME,
    ext_modules=EXT_MODULES,
    cmdclass=CMDCLASS,
)
