from setuptools import setup

setup(
    name='oink',
    version='1.0',
    author='Your Name Here',
    author_email="your@email.here",
    url='http://your.url/here',
    packages=["oink"],
    zip_safe=False,
    setup_requires=['setuptools'],
    install_requires=["desktop-app"],
    include_package_data=True,
    package_data={"": ['*.svg', '*.ico', 'desktop-app.json'],},
    entry_points={
        'console_scripts': [
            'oink = desktop_app:entry_point',
            'oink.honk = desktop_app:entry_point',
        ],
    },
)
