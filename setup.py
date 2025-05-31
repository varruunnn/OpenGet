from setuptools import setup, find_packages

setup(
    name='OpenGet',
    version='0.1.0',
    description='Open-Source Parallel Download Manager',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'requests>=2.26.0,<3.0.0',
        'tqdm>=4.0'
    ],
    entry_points={
        'console_scripts': [
            'OpenGet = cli:main'
        ]
    },
)
