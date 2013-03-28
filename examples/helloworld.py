# -*- coding: utf-8 -*-
"""
    helloworld
    ~~~~~~~~~~

    A minimal working example for :mod:`pyte`.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import sys
sys.path.append("..")

import pyte


if __name__ == "__main__":
    stream = pyte.Stream()
    screen = pyte.Screen(80, 24)
    stream.attach(screen)
    stream.feed("Hello World!")

    for idx, line in enumerate(screen.display, 1):
        print("{0:2d} {1} ¶".format(idx, line))
