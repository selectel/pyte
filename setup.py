#! /usr/bin/env python

import os

from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))

DESCRIPTION = "Simple VTXXX-compatible terminal emulator."

try:
    with open(os.path.join(here, "README")) as f:
        LONG_DESCRIPTION = f.read()
except IOError:
    LONG_DESCRIPTION = ""


CLASSIFIERS = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
    "Topic :: Terminals :: Terminal Emulators/X Terminals",
]


setup(name="pyte",
      version="0.8.2",
      packages=["pyte"],
      install_requires=["wcwidth"],
      setup_requires=["pytest-runner"],
      tests_require=["pytest"],
      python_requires=">=3.8",
      platforms=["any"],
      package_data={"pyte": ["py.typed"]},

      author="Sergei Lebedev",
      author_email="superbobry@gmail.com",
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      classifiers=CLASSIFIERS,
      keywords=["vt102", "vte", "terminal emulator"],
      url="https://github.com/selectel/pyte")
