from setuptools import setup, find_packages

setup(
    name='pyvault',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    setup_requires=[
        'setuptools-pipfile'
    ],
    use_pipfile=True,
    entry_points='''
        [console_scripts]
        pyvault=cli:__main__
    ''',
)
