from setuptools import setup

setup(
    name='oink',
    version='1.0',
    author='Old MacDonald',
    author_email="macdonald@eie.io",
    packages=["oink"],
    setup_requires=['setuptools'],
    install_requires=["desktop-app"],
    zip_safe=False,
    include_package_data=True,
    package_data={"": ['*.svg', '*.ico', 'desktop-app.json']},
    entry_points={
        'console_scripts': ['oink = desktop_app:entry_point'],
        'gui_scripts': ['oink-gui = desktop_app:entry_point'],
    },
)
