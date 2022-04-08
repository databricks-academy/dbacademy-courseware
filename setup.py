import setuptools
from setuptools import find_packages

setuptools.setup(
    name="dbacademy-courseware",
    version="0.1",
    package_dir={"dbacademy": "src"},
    packages=find_packages(),
    # packages=["dbacademy", "dbacademy.dbtest", "dbacademy.dbrest"],
)
