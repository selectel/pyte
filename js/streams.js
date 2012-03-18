// -*- coding: utf-8 -*-
/*
    pyte.streams
    ~~~~~~~~~~~~

    This module provides three stream implementations with different
    features; for starters, here's a quick example of how streams are
    typically used:

    >>> import pyte
    >>>
    >>> class Dummy(object):
    ...     def __init__(self):
    ...         self.y = 0
    ...
    ...     def cursor_up(self, count=None):
    ...         self.y += count or 1
    ...
    >>> dummy = Dummy()
    >>> stream = pyte.Stream()
    >>> stream.attach(dummy)
    >>> stream.feed(u"\u001B[5A")  // Move the cursor up 5 rows.
    >>> dummy.y
    5

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
*/

if (!Function.prototype.bind) {
    Function.prototype.bind = function (scope) {
        var _function = this;

        return function () {
            return _function.apply(scope, arguments);
        }
    };
}


function Stream() {
    /*
    A stream is a state machine that parses a stream of characters
        and dispatches events based on what it sees.

        .. note::

           Stream only accepts unicode strings as input, but if, for some
           reason, you need to feed it with byte strings, consider using
           :class:`~pyte.streams.ByteStream` instead.

        .. seealso::

            `man console_codes <http://linux.die.net/man/4/console_codes>`_
                For details on console codes listed bellow in :attr:`basic`,
                :attr:`escape`, :attr:`csi` and :attr:`sharp`.
    */

    this.__init__();
}

Stream.prototype = {
    //: Control sequences, which don't require any arguments.
    basic: {},
    //: non-CSI escape sequences.
    escape: {},
    //: "sharp" escape sequences -- ``ESC // <N>``.
    sharp: {},
    //: CSI escape sequences -- ``CSI P1;P2;...;Pn <fn>``.
    csi: {},
    __init__: function() {
        this.handlers = {
            "stream": this._stream.bind(this),
            "escape": this._escape.bind(this),
            "arguments": this._arguments.bind(this),
            "sharp": this._sharp.bind(this),
            "charset": this._charset.bind(this)
        };

        this.listeners = [];
        this.reset();
    },
    reset: function() {
        /* Reset state to ``"stream"`` and empty parameter attributes.*/
        this.state = "stream";
        this.flags = {};
        this.params = [];
        this.current = "";
    },
    consume: function(ch) {
        /* Consume a single unicode character and advance the state as
        necessary.
        */

        try {
            this.handlers[this.state](ch)
        } catch (e) {
            window.console && console.log(e);
            /* python code:
            except TypeError:
                pass
            except KeyError:
                if __debug__:
                    self.flags["state"] = self.state
                    self.flags["unhandled"] = char
                    self.dispatch("debug", *self.params)
                    self.reset()
                else:
                    raise
            */
        }
    },
    feed: function(chars) {
        for (var i = 0; i < chars.length; i++) {
            this.consume(chars.charAt(i))
        }
    },
    attach: function(screen, only) {
        if (only) throw new Error("'only' is not implemented")
        this.listeners.push(screen)
    },
    detach: function(screen) {
        throw new Error("Not implemented")
    },
    dispatch: function(event, args, kwargs) {
        args = args || [];
        kwargs = kwargs || {};
        var listener, handler;
        for (var i = 0; i < this.listeners.length; i++) {
            listener = this.listeners[i];
            handler = listener[event];
            if (!handler) continue;
            if (listener.__before__) listener.__before__(event);
            handler.apply(listener, args); // yes, we ignore this.flags by now
            if (listener.__after__) listener.__after__(event);
        }
        if (kwargs.reset === true || kwargs.reset === undefined) {
            this.reset();
        }
    },
    _stream: function(ch) {
        if (ch in this.basic) this.dispatch(this.basic[ch], []);
        else if(ch == ESC) this.state = "escape";
        else if(ch == CSI) this.state = "arguments";
        else if (ch != NUL && ch != DEL) this.dispatch("draw", [ch]);
    },
    _escape: function(ch) {
        if (ch == "#") {
            this.state = "sharp";
        } else if (ch == "[") {
            this.state = "arguments";
        } else if (ch == "(" || ch == ")") {
            this.state = "charset";
            this.flags["mode"] = ch;
        } else {
            this.dispatch(this.escape[ch]);
        }
    },
    _sharp: function(ch) {
        this.dispatch(this.sharp[ch]);
    },
    _charset: function(ch) {
        this.dispatch("set_charset", [ch]);
    },
    __isDigit: function(ch) {
        var code = ch.charCodeAt(0);
        return code > 47 && code < 58;
    },
    _arguments: function(ch) {
        /*
        Parse arguments of an escape sequence.

        All parameters are unsigned, positive decimal integers, with
        the most significant digit sent first. Any parameter greater
        than 9999 is set to 9999. If you do not specify a value, a 0
        value is assumed.

        .. seealso::

           `VT102 User Guide <http://vt100.net/docs/vt102-ug/>`_
               For details on the formatting of escape arguments.

           `VT220 Programmer Reference <http://http://vt100.net/docs/vt220-rm/>`_
               For details on the characters valid for use as arguments.
        */
        if (ch == "?") {
            this.flags['private'] = true;
        } else if (ch == BEL || ch == BS || ch == HT || ch == LF || ch == VT || ch == FF || ch == CR) {
            this.dispatch(this.basic[ch], [], {reset: false});
        } else if (ch == SP) {
            return;
        } else if (ch == CAN || ch == SUB) {
            this.dispatch("draw", ch);
            this.state = "stream";
        } else if (this.__isDigit(ch)) {
            this.current += ch;
        } else {
            this.params.push(Math.min(parseInt(this.current || 0), 9999));

            if (ch == ';') this.current = "";
            else           this.dispatch(this.csi[ch], this.params);
        }
    }
};

Stream.prototype.basic[BEL] = "bell";
Stream.prototype.basic[BS] = "backspace";
Stream.prototype.basic[HT] = "tab";
Stream.prototype.basic[LF] = "linefeed";
Stream.prototype.basic[VT] = "linefeed";
Stream.prototype.basic[FF] = "linefeed";
Stream.prototype.basic[CR] = "carriage_return";
Stream.prototype.basic[SO] = "shift_out";
Stream.prototype.basic[SI] = "shift_in";

Stream.prototype.escape[RIS] = "reset";
Stream.prototype.escape[IND] = "index";
Stream.prototype.escape[NEL] = "linefeed";
Stream.prototype.escape[RI] = "reverse_index";
Stream.prototype.escape[HTS] = "set_tab_stop";
Stream.prototype.escape[DECSC] = "save_cursor";
Stream.prototype.escape[DECRC] = "restore_cursor";

Stream.prototype.sharp[DECALN] = "alignment_display";

Stream.prototype.csi[ICH] = "insert_characters";
Stream.prototype.csi[CUU] = "cursor_up";
Stream.prototype.csi[CUD] = "cursor_down";
Stream.prototype.csi[CUF] = "cursor_forward";
Stream.prototype.csi[CUB] = "cursor_back";
Stream.prototype.csi[CNL] = "cursor_down1";
Stream.prototype.csi[CPL] = "cursor_up1";
Stream.prototype.csi[CHA] = "cursor_to_column";
Stream.prototype.csi[CUP] = "cursor_position";
Stream.prototype.csi[ED] = "erase_in_display";
Stream.prototype.csi[EL] = "erase_in_line";
Stream.prototype.csi[IL] = "insert_lines";
Stream.prototype.csi[DL] = "delete_lines";
Stream.prototype.csi[DCH] = "delete_characters";
Stream.prototype.csi[ECH] = "erase_characters";
Stream.prototype.csi[HPR] = "cursor_forward";
Stream.prototype.csi[VPA] = "cursor_to_line";
Stream.prototype.csi[VPR] = "cursor_down";
Stream.prototype.csi[HVP] = "cursor_position";
Stream.prototype.csi[TBC] = "clear_tab_stop";
Stream.prototype.csi[SM] = "set_mode";
Stream.prototype.csi[RM] = "reset_mode";
Stream.prototype.csi[SGR] = "select_graphic_rendition";
Stream.prototype.csi[DECSTBM] = "set_margins";
Stream.prototype.csi[HPA] = "cursor_to_column";
