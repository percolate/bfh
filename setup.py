#!/usr/bin/env python

from setuptools import setup
from bfh.version import VERSION

setup(
    name='bfh',
    version=VERSION,
    description="Smacks schemas into other schemas",
    author="Evan Bender",
    install_requires=[
        "python-dateutil",
    ],
    author_email="evan.bender@percolate.com",
    url="https://github.com/percolate/bfh",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 2.7",
    ],
    packages=["bfh"],
)
