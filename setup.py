# Databricks notebook source
import setuptools

setuptools.setup(
    name="dbacademy-courseware",
    version="0.1",
    package_dir={"dbacademy": "src"},
    packages=["dbacademy.dbpublish", "dbacademy.dbtest"],
)
