from pathlib import Path
from setuptools import setup, find_packages


setup(
    name='inmates',
    description='a CLI tool for listing inmates',
    version_format='{tag}.dev{commitcount}+{gitsha}',
    setup_requires=[
        'setuptools-git-version==1.0.3'
    ],
    packages=find_packages(exclude=['tests']),
    package_data={'inmates': [str(Path('inmates.csv').absolute())]},
    maintainer='Emmanuel I. Obi',
    maintainer_email='withtwoemms@gmail.com',
    url='',
    include_package_data=True,
    entry_points="""
        [console_scripts]
        inmates=inmates.cli:cli
    """,
)
