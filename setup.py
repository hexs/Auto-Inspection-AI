from setuptools import setup, find_packages
from AutoInspection import __version__ as version

setup(
    name='AutoInspection',
    version=version,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    url='https://github.com/hexs/Auto-Inspection-AI',
)
