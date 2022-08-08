import setuptools
from setuptools import find_packages

reqs = [
    "requests",
    "dbacademy-rest@git+https://github.com/databricks-academy/dbacademy-rest",
]

setuptools.setup(
    name="dbacademy-courseware",
    version="0.1",
    install_requires=reqs,
    package_dir={"": "src"},
    packages=find_packages(where="src")
)
