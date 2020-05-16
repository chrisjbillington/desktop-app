import os
from setuptools import setup, Extension
import platform
WINDOWS = platform.system() == 'Windows'

try:
    from setuptools_conda import dist_conda
except ImportError:
    dist_conda = None

INSTALL_REQUIRES = [
    "setuptools_scm",
    "pywin32;               sys_platform == 'win32'",
    "importlib_metadata;    python_version < '3.8'",
]

wineventhook = Extension(
    'desktop_app.wineventhook',
    sources=[os.path.join('src', 'wineventhook.cpp')],
    libraries=["user32", "shell32", "ole32"],
)

setup(
    name='desktop-app',
    use_scm_version=(
        {'local_scheme': 'no-local-version'} if os.getenv('GITHUB_ACTIONS') else True
    ),
    description=(
        "OS menu shortcuts, correct taskbar behaviour, and environment "
        + "activation for Python GUI apps"
    ),
    long_description=open('README.md', encoding='utf8').read(),
    long_description_content_type='text/markdown',
    author='Chris Billington',
    author_email='chrisjbillington@gmail.com ',
    url='http://github.com/chrisjbillington/desktop-app',
    license="BSD",
    packages=["desktop_app"],
    ext_modules=[wineventhook] if WINDOWS else [],
    zip_safe=False,
    setup_requires=['setuptools', 'setuptools_scm'],
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=INSTALL_REQUIRES if 'CONDA_BUILD' not in os.environ else [],
    entry_points={'console_scripts': ['desktop-app = desktop_app.__main__:main',],},
    cmdclass={'dist_conda': dist_conda} if dist_conda is not None else {},
    command_options={
        'dist_conda': {
            'pythons': (__file__, ['3.6', '3.7', '3.8']),
            'platforms': (__file__, ['linux-64', 'win-32', 'win-64', 'osx-64']),
            'force_conversion': (__file__, True),
        },
    },
)
