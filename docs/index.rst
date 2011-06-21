.. pyte documentation master file, created by
   sphinx-quickstart on Fri Apr  8 12:49:51 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyte's documentation!
=================================

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


Usage
=====

There are two important classes in ``pyte``:
:class:`~pyte.screens.Screen` and :class:`~pyte.streams.Stream`. The
``Screen`` is the terminal screen emulator. It maintains an in-memory
buffer of text and text-attributes to display on screen. The ``Stream``
is the stream processor. It manages the state of the input and dispatches
events to anything that's listening about things that are going on.
Events are things like ``LINEFEED``, ``DRAW "a"``, or ``CURSOR_POSITION 10 10``.
See the :ref:`API <api>` for more details.

In general, if you just want to know what's being displayed on screen you
can do something like the following:

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

.. _api:

API
===

.. automodule:: pyte.streams
    :members:

.. automodule:: pyte.screens
    :members:

.. automodule:: pyte.modes
    :members:

.. automodule:: pyte.control
    :members:

.. automodule:: pyte.escape
    :members:

.. automodule:: pyte.graphics
    :members:

.. automodule:: pyte.charsets
    :members:
