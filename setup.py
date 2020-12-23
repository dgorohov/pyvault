from setuptools import setup, find_packages
from vault.version import version as ver

setup(
    name='pyvault',
    version=f'{ver}',
    packages=find_packages(),
    include_package_data=True,
    package_data={'vault.prompt.qt': ['prompt.ui']},
    setup_requires=[
        'setuptools-pipfile'
    ],
    use_pipfile=True,
    entry_points='''
        [console_scripts]
        pyvault=vault.cli:cli
    ''',
)
