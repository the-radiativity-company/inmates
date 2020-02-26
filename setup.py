from setuptools import setup, find_packages


setup(
    name='inmates',
    version='0.0.1',
    description='a CLI tool for listing inmates',
    packages=find_packages(),
    maintainer='Emmanuel I. Obi',
    maintainer_email='withtwoemms@gmail.com',
    url='',
    include_package_data=True,
    install_requires=[
        'click==7.0',
        'httpx==0.11.1'
    ],
    entry_points="""
        [console_scripts]
        inmates=inmates.cli:cli
    """,
)
