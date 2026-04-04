from __future__ import annotations
from enum import IntFlag


class KeyboardFlags(IntFlag):
    DEFAULT = 0
    """
    All progressive enhancements disabled
    """

    DISAMBIGUATE_ESCAPE_CODES = 1
    """
    This type of progressive enhancement (0b1) fixes the problem of some legacy
    key press encodings overlapping with other control codes. For instance,
    pressing the Esc key generates the byte 0x1b which also is used to indicate
    the start of an escape code. Similarly pressing the key alt+[ will generate
    the bytes used for CSI control codes.

    Turning on this flag will cause the terminal to report the Esc, alt+key,
    ctrl+key, ctrl+alt+key, shift+alt+key keys using CSI u sequences instead of
    legacy ones. Here key is any ASCII key as described in Legacy text keys.
    Additionally, all non text keypad keys will be reported as separate keys
    with CSI u encoding, using dedicated numbers from the table below.

    With this flag turned on, all key events that do not generate text are
    represented in one of the following two forms:

    .. code:

        CSI number; modifier u
        CSI 1; modifier [~ABCDEFHPQS]

    This makes it very easy to parse key events in an application. In
    particular, ctrl+c will no longer generate the SIGINT signal, but instead
    be delivered as a CSI u escape code. This has the nice side effect of
    making it much easier to integrate into the application event loop. The
    only exceptions are the Enter, Tab and Backspace keys which still generate
    the same bytes as in legacy mode this is to allow the user to type and
    execute commands in the shell such as reset after a program that sets this
    mode crashes without clearing it. Note that the Lock modifiers are not
    reported for text producing keys, to keep them useable in legacy programs.
    To get lock modifiers for all keys use the Report all keys as escape codes
    enhancement.
    """

    REPORT_EVENT_TYPES = 2
    """
    This progressive enhancement (0b10) causes the terminal to report key
    repeat and key release events. Normally only key press events are reported
    and key repeat events are treated as key press events. See Event types for
    details on how these are reported.
    """

    REPORT_ALTERNATE_KEYS = 4
    """
    This progressive enhancement (0b100) causes the terminal to report
    alternate key values in addition to the main value, to aid in shortcut
    matching. See Key codes for details on how these are reported. Note that
    this flag is a pure enhancement to the form of the escape code used to
    represent key events, only key events represented as escape codes due to
    the other enhancements in effect will be affected by this enhancement. In
    other words, only if a key event was already going to be represented as an
    escape code due to one of the other enhancements will this enhancement
    affect it.
    """

    REPORT_ALL_KEYS_AS_ESCAPE_CODES = 8
    """
    Key events that generate text, such as plain key presses without modifiers,
    result in just the text being sent, in the legacy protocol. There is no way
    to be notified of key repeat/release events. These types of events are
    needed for some applications, such as games (think of movement using the
    WASD keys).

    This progressive enhancement (0b1000) turns on key reporting even for key
    events that generate text. When it is enabled, text will not be sent,
    instead only key events are sent. If the text is needed as well, combine
    with the Report associated text enhancement below.

    Additionally, with this mode, events for pressing modifier keys are
    reported. Note that all keys are reported as escape codes, including Enter,
    Tab, Backspace etc. Note that this enhancement implies all keys are
    automatically disambiguated as well, since they are represented in their
    canonical escape code form.
    """

    REPORT_ASSOCIATED_TEXT = 16
    """
    This progressive enhancement (0b10000) additionally causes key events that
    generate text to be reported as CSI u escape codes with the text embedded
    in the escape code. See Text as code points above for details on the
    mechanism. Note that this flag is an enhancement to Report all keys as
    escape codes and is undefined if used without it.
    """
