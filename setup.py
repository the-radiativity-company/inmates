from setuptools import setup, find_packages


setup(
    name='inmates',
    description='a CLI tool for listing inmates',
    version_format='{tag}.dev{commitcount}+{gitsha}',
    setup_requires=[
        'setuptools-git-version'
    ],
    packages=find_packages(),
    maintainer='Emmanuel I. Obi',
    maintainer_email='withtwoemms@gmail.com',
    url='',
    include_package_data=True,
    install_requires=[
        'click==7.0',
        'python-magic==0.4.15',
        'httpx==0.11.1'
    ],
    entry_points="""
        [console_scripts]
        inmates=inmates.cli:cli
    """,
)
