import os
from setuptools import setup, Extension
import platform

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
    ext_modules=EXT_MODULES,
)
