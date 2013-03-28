# -*- coding: utf-8 -*-
"""
    debug
    ~~~~~

    ... what if I need to debug a bunch of escape sequences? Just use
    :class:`~pyte.streams.DebugStream` instead of the usual
    :class:`~pyte.streams.Stream`. Note though, that it requires
    :func:`bytes` as input.

    :copyright: (c) 2011-2013 by Selectel, see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import print_function, unicode_literals

import sys
sys.path.append("..")

import pyte

# A blob of `ADOM` output we need to debug. Hey! I know this is ugly ...
blob = b"""\x1b[25d\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[23;15H\x1b[37m\x1b[40mSt:28  Le: 1  Wi: 8  Dx:12  To:31  Ch: 3  Ap: 5  Ma: 9  Pe:11 C\x08\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[5d\x08\x08\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mA\x1b[5;75H\x1b[33m\x1b[40m.\x1b[6d\x08\x1b[0;10;1m\x1b[30m\x1b[40m@\x1b[7;73H^\x1b[8d\x1b[0;10m\x1b[33m\x1b[40m.\x1b[H\x1b[C\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mroad.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[6;75H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mA\x1b[5;72H\x1b[0;10;1m\x1b[37m\x1b[40m^\x1b[6d\x08^\x1b[30m\x1b[40m^@\x1b[0;10m\x1b[33m\x1b[40m.\x1b[7;72H\x1b[0;10;1m\x1b[30m\x1b[40m^\x1b[8d\x1b[0;10m\x1b[33m\x1b[40m..\x1b[0;10;1m\x1b[37m\x1b[40m^\x1b[H\x1b[C\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mroad.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[6;74H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mYou\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mneed\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mspecial\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mequipment\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mto\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mscale\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mthose\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mmountains.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[6;74H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mYou\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mneed\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mspecial\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mequipment\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mto\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mscale\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mthose\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mmountains.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[6;74H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mA\x1b[6;74H\x1b[33m\x1b[40m.\x1b[7d\x08\x1b[0;10;1m\x1b[30m\x1b[40m@\x1b[8;72H\x1b[0;10m\x1b[33m\x1b[40m.\x1b[9d\x1b[0;10;1m\x1b[30m\x1b[40m^\x1b[37m\x1b[40m^^\x1b[H\x1b[C\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mroad.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[7;74H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mYou\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mneed\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mspecial\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mequipment\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mto\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mscale\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mthose\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mmountains.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[7;74H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mA\x1b[7;74H\x1b[33m\x1b[40m.\x1b[8d\x08\x1b[0;10;1m\x1b[30m\x1b[40m@\x1b[9;72H\x1b[0;10m\x1b[33m\x1b[40m~\x1b[10d\x1b[0;10;1m\x1b[30m\x1b[40m^\x1b[H\x1b[C\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mroad.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[8;74H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mA\x1b[7;71H\x1b[0;10;1m\x1b[30m\x1b[40m^\x1b[8d\x08\x1b[0;10m\x1b[33m\x1b[40m..\x1b[0;10;1m\x1b[30m\x1b[40m@\x1b[0;10m\x1b[33m\x1b[40m.\x1b[9;71H.\x1b[10d\x1b[32m\x1b[40m&\x1b[0;10;1m\x1b[30m\x1b[40m^^\x1b[H\x1b[C\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mroad.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[8;73H\x1b[?25h\x1b[?0c\x1b[?25l\x1b[?1c\x1b[H\x1b[K\x1b[2d\x1b[A\x1b[37m\x1b[40mA\x1b[6;71H\x1b[0;10;1m\x1b[37m\x1b[40m^\x1b[7d\x08\x08\x1b[30m\x1b[40m^\x1b[8d\x08^\x1b[0;10m\x1b[33m\x1b[40m.\x1b[0;10;1m\x1b[30m\x1b[40m@\x1b[0;10m\x1b[33m\x1b[40m.\x1b[9;70H.\x1b[10d\x1b[32m\x1b[40m&\x1b[H\x1b[C\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[C\x1b[37m\x1b[40mroad.\x1b[0;10m\x1b[39;49m\x1b[37m\x1b[40m\x1b[24;78H\x1b[8;72H\x1b[?25h\x1b[?0c"""


if __name__ == "__main__":
    stream = pyte.DebugStream()
    screen = pyte.Screen(80, 24)
    stream.attach(screen)
    stream.feed(blob)
