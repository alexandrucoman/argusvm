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
    author="Cloudbase Solutions Srl",
    url="https://www.cloudbase.it/",
    long_description=open("README.md").read(),
    packages=["arestor", "arestor.client", "arestor.worker"],
    scripts=["scripts/arestor"],
    requires=["six", "neutron"],
    data_files=[
        ("share/doc/arestor", "resources/tempest.conf"),
    ],
    maintainer="Alexandru Coman",
    maintainer_email="acoman@cloudbasesolutions.com"
)
