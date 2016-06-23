#! /usr/bin/env python
"""Arestor install script."""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name="arestor",
    version="0.1",
    description="Various tools for the Argus-CI framework.",
    long_description=open("README.md").read(),
    author="Cloudbase Solutions Srl",
    url="http://www.cloudbase.it/",
    packages=["arestor", "arestor.client", "arestor.resources",
              "arestor.worker"],
    scripts=["scripts/arestor"],
    requires=["six", "neutron"]
)
