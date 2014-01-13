#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


here = os.path.abspath(os.path.dirname(__file__))

DESCRIPTION = "Simple VTXXX-compatible terminal emulator."

try:
    LONG_DESCRIPTION = open(os.path.join(here, "README")).read()
except IOError:
    LONG_DESCRIPTION = ""


CLASSIFIERS = (
    "Development Status :: 5 - Production/Stable",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.3",
    "Topic :: Terminals :: Terminal Emulators/X Terminals",
)


class PyTest(TestCommand):
    """Unfortunately :mod:`setuptools` support only :mod:`unittest`
    based tests, thus, we have to overider build-in ``test`` command
    to run :mod:`pytest`.
    """
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.exit(pytest.main(self.test_args + ["./tests"]))


setup(name="pyte",
      version="0.4.8",
      packages=["pyte"],
      cmdclass={"test": PyTest},
      tests_require=["pytest"],
      platforms=["any"],

      author="Sergei Lebedev",
      author_email="superbobry@gmail.com",
      description=DESCRIPTION,
      long_description=LONG_DESCRIPTION,
      classifiers=CLASSIFIERS,
      keywords=["vt102", "vte", "terminal emulator"],
      url="https://github.com/selectel/pyte",
)
