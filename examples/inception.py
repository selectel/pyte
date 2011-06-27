# -*- coding: utf-8 -*-
"""
    inception
    ~~~~~~~~~

    A terminal emulator within a terminal emulator within a terminal
    emulator -- tiny example to show how pagination works.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import random
import sys
sys.path.append("..")

import pyte


def print_screen(screen, text):
    print(pyte.ctrl.ESC + pyte.esc.RIS)

    for idx, line in enumerate(screen.display, 1):
        print("{0:2d} {1} ¶".format(idx, line))

    raw_input("\n\n" + text)


if __name__ == "__main__":
    stream = pyte.Stream()  #             v -- means scroll whole page.
    screen = pyte.HistoryScreen(80, 24, ratio=1)
    stream.attach(screen)

    stream.feed("".join(random.choice("ABCDEFG \n") for _ in xrange(80 * 24 * 5)))

    print_screen(screen, "Hit ENTER to move up!")
    screen.prev_page()
    print_screen(screen, "Hit ENTER to move back down!")
    screen.next_page()
    print_screen(screen, "OK?")
