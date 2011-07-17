.. _tutorial:

Tutorial
--------

There are two important classes in ``pyte``: :class:`~pyte.screens.Screen`
and :class:`~pyte.streams.Stream`. The `Screen` is the terminal screen
emulator. It maintains an in-memory buffer of text and text-attributes
to display on screen. The `Stream` is the stream processor. It manages
the state of the input and dispatches events to anything that's listening
about things that are going on. Events are things like ``LINEFEED``,
``DRAW "a"``, or ``CURSOR_POSITION 10 10``. See the :ref:`API reference <api>`
for more details.

In general, if you just want to know what's being displayed on screen you
can do something like the following:

    >>> import pyte
    >>> screen = pyte.Screen(80, 24)
    >>> stream = pyte.Stream()
    >>> stream.attach(screen)
    >>> stream.feed("Hello World!")
    >>> screen.display
        ['Hello World!                                                                    ',
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
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ',
         '                                                                                ']


**Note**: ``Screen`` has no idea what is the source of bytes, fed into ``Stream``,
so, obviously, it **can't read** or **change** environment variables, which implies
that:

* it doesn't adjust `LINES` and `COLUMNS` on ``"resize"`` event;
* it doesn't use locale settings (`LC_*` and `LANG`);
* it doesn't use `TERM` value and expects it to be `"linux"` and only `"linux"`.
