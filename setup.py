from setuptools import setup, find_packages

setup(
    name='goocsv',
    version='0.1.0',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'goocsv = goocsv:main'
        ]
    }
)
