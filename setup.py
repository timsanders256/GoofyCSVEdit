from setuptools import setup, find_packages

setup(
    name='goocsv',
    version='0.2.0',
    packages=find_packages(),
    package_data={
        "goocsv": ["logo.png"]
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'goocsv = goocsv:main'
        ]
    }
)

