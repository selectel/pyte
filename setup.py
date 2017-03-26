#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os

from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))

DESCRIPTION = "Simple VTXXX-compatible terminal emulator."

try:
    LONG_DESCRIPTION = open(os.path.join(here, "README")).read()
except IOError:
    LONG_DESCRIPTION = ""


CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Topic :: Terminals :: Terminal Emulators/X Terminals",
]


setup(name="pyte",
      version="0.6.0",
      packages=["pyte"],
      install_requires=["wcwidth"],
      setup_requires=["pytest-runner"],
      tests_require=["pytest"],
      platforms=["any"],

      author="Sergei Lebedev",
      author_email="superbobry@gmail.com",
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      classifiers=CLASSIFIERS,
      keywords=["vt102", "vte", "terminal emulator"],
      url="https://github.com/selectel/pyte")
