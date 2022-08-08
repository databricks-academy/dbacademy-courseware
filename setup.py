import setuptools
from setuptools import find_packages

reqs = [
    "requests",
    "dbacademy-rest@git+https://github.com/databricks-academy/dbacademy-rest",
]


def find_dbacademy_packages():
    packages = find_packages(where="src")

    if "dbacademy" in packages:
        del packages[packages.index("dbacademy")]

    print("-"*80)
    print(packages)
    print("-"*80)
    return packages


setuptools.setup(
    name="dbacademy-courseware",
    version="0.1",
    install_requires=reqs,
    package_dir={"": "src"},
    packages=find_dbacademy_packages()
)
