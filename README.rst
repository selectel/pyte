::
     _______  __   __  _______  _______
    |       ||  | |  ||       ||       |
    |    _  ||  |_|  ||_     _||    ___|
    |   |_| ||       |  |   |  |   |___
    |    ___||_     _|  |   |  |    ___|
    |   |      |   |    |   |  |   |___
    |___|      |___|    |___|  |_______|

    -- `chicks dig dudes with terminals` (c) @samfoo


About
-----

What is ``pyte``? It's an in memory VTXXX-compatible terminal emulator.
*XXX* stands for a series video terminals, developed by
`DEC <http://en.wikipedia.org/wiki/Digital_Equipment_Corporation>`_ between
1970 and 1995. The first, and probably the most famous one, was VT100
terminal, which is now a de-facto standard for all virtual terminal
emulators. ``pyte`` follows the suit.

So, why would one need a terminal emulator library?

* To screen scrape terminal apps, for example ``htop`` or ``aptitude``.
* To write cross platform terminal emulators; either with a graphical
  (`xterm <http://invisible-island.net/xterm/>`_,
  `rxvt <http://www.rxvt.org/>`_) or a web interface, like
  `AjaxTerm <http://antony.lesuisse.org/software/ajaxterm/>`_.
* To have fun, hacking on the ancient, poorly documented technologies.

**Note**: ``pyte`` started as a fork of `vt102 <http://github.com/samfoo/vt102`_,
which is an incomplete implementation of VT100 features.


Installation
------------

If you have `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_
you can use ``easy_install -U pyte``. Otherwise, you can download the source
from `GitHub <http://github.com/selectel/pyte>`_ and run ``python setup.py install``.


Example
-------

    >>> import pyte
    >>> screen = pyte.Screen(80, 24)
    >>> stream = pyte.Stream()
    >>> stream.attach(screen)
    >>> stream.feed(u"\u001b7\u001b[?47h\u001b)0\u001b[H\u001b[2J\u001b[H"
                    u"\u001b[2;1HNetHack, Copyright 1985-2003\r\u001b[3;1"
                    u"H         By Stichting Mathematisch Centrum and M. "
                    u"Stephenson.\r\u001b[4;1H         See license for de"
                    u"tails.\r\u001b[5;1H\u001b[6;1H\u001b[7;1HShall I pi"
                    u"ck a character's race, role, gender and alignment f"
                    u"or you? [ynq] ")
    >>> screen.display
        ['                                                                                ',
         'NetHack, Copyright 1985-2003                                                    ',
         '         By Stichting Mathematisch Centrum and M. Stephenson.                   ',
         '         See license for details.                                               ',
         '                                                                                ',
         '                                                                                ',
         "Shall I pick a character's race, role, gender and alignment for you? [ynq]      ",
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ']
    >>>


Options?
--------

``pyte`` is not alone in the weird world of terminal emulator libraries,
here's a few other options worth checking out:
`Termemulator <http://sourceforge.net/projects/termemulator/>`_,
`pyqonsole <http://hg.logilab.org/pyqonsole/>`_,
`webtty <http://code.google.com/p/webtty/>`_
`AjaxTerm <http://antony.lesuisse.org/software/ajaxterm/>`_
