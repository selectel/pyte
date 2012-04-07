/*
pyte.screens
~~~~~~~~~~~~

This module provides classes for terminal screens, currently
it contains three screens with different features:

* :class:`~pyte.screens.Screen` -- base screen implementation,
  which handles all the core escape sequences, recognized by
  :class:`~pyte.streams.Stream`.
* If you need a screen to keep track of the changed lines
  (which you probably do need) -- use
  :class:`~pyte.screens.DiffScreen`.
* If you also want a screen to collect history and allow
  pagination -- :class:`pyte.screen.HistoryScreen` is here
  for ya ;)

.. note:: It would be nice to split those features into mixin
          classes, rather than subclasses, but it's not obvious
          how to do -- feel free to submit a pull request.

:copyright: (c) 2011 Selectel, see AUTHORS for more details.
:license: LGPL, see LICENSE for more details.
*/

var namedlist = function(fields) { // something like namedtuple in python
    return function() {
        for(var i = 0; i < arguments.length; i++) {
            this[i] = arguments[i];
            this[fields[i]] = arguments[i];
        }
    };
};

function range() {
    var start, end, step;
    var array = [];

    switch (arguments.length) {
        case 0:
            throw new Error('range() expected at least 1 argument, got 0 - must be specified as [start,] stop[, step]');
            return array;
        case 1:
            start = 0;
            end = Math.floor(arguments[0]) - 1;
            step = 1;
            break;
        case 2:
        case 3:
        default:
            start = Math.floor(arguments[0]);
            end = Math.floor(arguments[1]) - 1;
            var s = arguments[2];
            if (typeof s === 'undefined') {
                s = 1;
            }
            step = Math.floor(s) || (function () {
                throw new Error('range() step argument must not be zero');
            })();
            break;
    }

    var i;
    if (step > 0) {
        for (i = start; i <= end; i += step) {
            array.push(i);
        }
    } else if (step < 0) {
        step = -step;
        if (start > end) {
            for (i = start; i > end + 1; i -= step) {
                array.push(i);
            }
        }
    }
    return array;
}

function repeat(num, obj) {
    var res = [];
    for (var i = 0; i < num; i++) res.push(obj);
    return res;
}

var Margins = namedlist(["top", "bottom"]);
var Savepoint = namedlist(["cursor","g0_charset","g1_charset","charset","origin","wrap"]);

var Char = function(data, attrs) {
    this.data = data;

    attrs = attrs || {};
    this.fg = attrs.fg || "default";
    this.bg = attrs.bg || "default";
    this.bold = attrs.bold || false;
    this.italics = attrs.italics || false;
    this.underscore = attrs.underscore || false;
    this.reverse = attrs.reverse || false;
    this.strikethrough = attrs.strikethrough || false;
};

var Cursor = function(x, y, attrs) {
    this.x = x;
    this.y = y;
    this.attrs = attrs || (new Char(" "));
    this.hidden = false;
};

var Screen = function() {
    var self = this;
    this.__init__.apply(this, arguments);
    /*
    // debug:
    for (var k in this) {
        if (typeof this[k] != 'function') continue;
        (function(k) {
            var orig = self[k];
            self[k] = function() {
                console.log(k, arguments);
                orig.apply(self, arguments);
            }
        })(''+k);

    }
    */
};

Screen.prototype = {
    default_char: new Char(" ", {fg: "default", "bg": "default"}),
    __init__: function(columns, lines) {
        this.savepoints = [];
        this.lines = lines;
        this.length = lines;
        this.columns = columns;
        this.reset();
    },
    __toString: function() {
        return "Screen("+this.columns+","+this.lines+")";
    },
    __before__: function(command) {

    },
    __after__: function(command) {

    },
    size: function() {
        return [this.lines, this.columns];
    },
    display: function() {
        /* Returns a :func:`list` of screen lines as unicode strings. */
        var lines = [];
        for (var i = 0; i < this.lines; i++) {
            var line = [];
            for (var j = 0; j < this.columns; j++) {
                line.push(this[i][j].data);
            }
            lines.push(line.join(""));
        }
        return lines;
    },
    reset: function() {
        var line;
        for (var i = 0; i < this.lines; i++) {
            line = [];
            for (var j = 0; j < this.columns; j++) line.push(this.default_char);
            this[i] = line;
        }
        this.mode = {};
        this.mode[DECAWM] = true;
        this.mode[DECTCEM] = true;
        this.mode[LNM] = true;

        this.margins = new Margins(0, this.lines - 1);

        this.charset = 0;
        this.g0_charset = IBMPC_MAP;
        this.g1_charset = VT100_MAP;

        var tabstops = range(8, this.columns, 8);
        this.tabstops = {};
        for (i = 0; i < tabstops.length; i++) this.tabstops[tabstops[i]] = true;

        this.cursor = new Cursor(0, 0);
        this.cursor_position();
    },
    resize: function(lines, columns) {
        lines = lines || this.lines;
        columns = columns || this.columns;

        var diff = this.lines - lines, i, y;

        if (diff < 0) {
            for (i = diff; i < 0; i++) {
                this.push(repeat(this.columns, this.default_char));
            }
        } else if (diff > 0) {
            for (i = 0; i < diff; i++) this.pop();
        }

        diff = this.columns - columns;

        if (diff < 0) {
            for (y = 0; y < lines; y++) {
                for (i = 0; i < -diff; i++) this[y].push(this.default_char);
            }
        } else if (diff > 0) {
            for (y = 0; y < lines; y++) {
                this[y].splice(0, diff);
            }
        }

        this.lines = lines;
        this.columns = columns;
        this.margins = new Margins(0, this.lines - 1);
        this.reset_mode(DECOM);
    },
    set_margins: function(top, bottom) {
        if (top === undefined || bottom === undefined) {
            return;
        }

        top = Math.max(0, Math.min(top - 1, this.lines - 1));
        bottom = Math.max(0, Math.min(bottom - 1, this.lines - 1));

        if (bottom - top >= 1) {
            this.margins = new Margins(top, bottom);
            this.cursor_position();
        }
    },
    set_charset: function(code, mode) {
        var charsetmap = {"(": "g0_charset", ")": "g1_charset"};

        if (code in MAPS) {
            this[charsetmap[mode]] = MAPS[code];
        }
    },
    set_mode: function() {
        var modes = arguments;
        var kwargs = {}; // sorry, "private" mode is ignored this way
        var i, j;
        if (kwargs['private']) {
            var modes_tmp = [];
            for (i = 0; i < modes.length; i++) {
                modes_tmp.push(modes[i] << 5);
            }
            modes = modes_tmp;
        }

        for (i = 0; i < modes.length; i++) this.mode[modes[i]] = true;

        if (modes[DECCOLM]) {
            this.resize(null, 132);
            this.erase_in_display(2);
            this.cursor_position();
        }

        if (modes[DECOM]) this.cursor_position();

        if (modes[DECSCNM]) {
            for (i = 0; i < this.lines; i++) {
                for (j = 0; j < this.columns; j++) {
                    this[i][j].reverse = true;
                }
            }
            this.select_graphic_rendition(_SGR["+reverse"]);
        }

        if (modes[DECTCEM]) this.cursor.hidden = false;
    },
    reset_mode: function() {
        var modes = arguments;
        var kwargs = {}; // sorry, "private" mode is ignored this way

        var i, j;
        if (kwargs['private']) {
            var modes_tmp = [];
            for (i = 0; i < modes.length; i++) {
                modes_tmp.push(modes[i] << 5);
            }
            modes = modes_tmp;
        }

        for (i = 0; i < modes.length; i++) this.mode[modes[i]] = false;

        if (modes[DECCOLM]) {
            this.resize(null, 80);
            this.erase_in_display(2);
            this.cursor_position();
        }

        if (modes[DECOM]) this.cursor_position();

        if (modes[DECSCNM]) {
            for (i = 0; i < this.lines; i++) {
                for (j = 0; j < this.columns; j++) {
                    this[i][j].reverse = false;
                }
            }
            this.select_graphic_rendition(_SGR["-reverse"]);
        }

        if (modes[DECTCEM]) this.cursor.hidden = true;
    },
    shift_in: function() {
        this.charset = 0;
    },
    shift_out: function() {
        this.charset = 1;
    },
    draw: function(ch) {
        var translate_tbl = [this.g0_charset,this.g1_charset][this.charset];
        ch = translate_tbl[ch.charCodeAt(0)] || ch;

        if (this.cursor.x == this.columns) {
            if (this.mode[DECAWM]) this.linefeed();
            else this.cursor.x -= 1;
        }

        if (this.mode[IRM]) this.insert_characters(1);

        this[this.cursor.y][this.cursor.x] = new Char(ch, this.cursor.attrs);

        this.cursor.x += 1;
    },
    carriage_return: function() {
        this.cursor.x = 0;
    },
    insert: function(idx, el) {
        Array.prototype.splice.call(this, idx, 0, el);
    },
    pop: function(idx) {
        Array.prototype.splice.call(this, idx, 1);
    },
    push: function(item) {
        this.insert(this.length - 1, item);
    },
    index: function() {
        var top = this.margins.top, bottom = this.margins.bottom;

        if (this.cursor.y == bottom) {
            this.pop(top);
            this.insert(bottom, repeat(this.columns, this.default_char));
        } else {
            this.cursor_down();
        }
    },
    reverse_index: function() {
        var top = this.margins.top, bottom = this.margins.bottom;

        if (this.cursor.y == top) {
            this.pop(bottom);
            this.insert(top, repeat(this.columns, this.default_char));
        } else {
            this.cursor_up();
        }
    },
    linefeed: function() {
        this.index();

        if (this.mode[LNM]) this.carriage_return();
    },
    /*
    Move to the next tab space, or the end of the screen if there
    aren't anymore left.
    note: this is a more optimized version than original implementation
    */
    tab: function() {
        for (var i = this.cursor.x + 1; i < this.columns - 1; i++) {
            if (this.tabstops[i]) break;
        }

        this.cursor.x = Math.min(i, this.columns - 1);
    },
    backspace: function() {
        this.cursor_back();
    },
    save_cursor: function() {
        var c = this.cursor;
        var cursor_copy = new Cursor(c.x, c.y, new Char(c.attrs.data, c.attrs));
        this.savepoints.push(
            new Savepoint(
                cursor_copy,
                this.g0_charset,
                this.g1_charset,
                this.charset,
                this.mode[DECOM],
                this.mode[DECAWM]
            )
        );
    },
    restore_cursor: function() {
        if (this.savepoints) {
            var savepoint = this.savepoints.pop();

            this.g0_charset = savepoint.g0_charset;
            this.g1_charset = savepoint.g1_charset;
            this.charset = savepoint.charset;

            if (savepoint.origin) this.set_mode(DECOM);
            if (savepoint.wrap) this.set_mode(DECAWM);

            this.cursor = savepoint.cursor;
            this.ensure_bounds(true);
        } else {
            this.reset_mode(DECOM);
            this.cursor_position();
        }
    },
    insert_lines: function(count) {
        count = count || 1;
        var top = this.margins.top, bottom = this.margins.bottom;

        if (top <= this.cursor.y && this.cursor.y <= bottom) {
            var line_min = this.cursor.y;
            var line_max = Math.min(bottom + 1, this.cursor.y + count);
            for (var i = line_min; i < line_max; i++) {
                this.pop(bottom);
                this.insert(i, repeat(this.columns, this.default_char));
            }

            this.carriage_return();
        }
    },
    delete_lines: function(count) {
        count = count || 1;
        var top = this.margins.top, bottom = this.margins.bottom;

        if (top <= this.cursor.y && this.cursor.y <= bottom) {
            var cnt = Math.min(bottom - self.cursor.y, count);
            for (var i = 0; i < cnt; i++) {
                this.pop(this.cursor.y);
                this.insert(bottom, repeat(this.columns, this.cursor.attrs));
            }
            this.carriage_return();
        }
    },
    insert_characters: function(count) {
        count = Math.min(this.columns - this.cursor.x, count || 1);
        for (var i = 0; i < count; i++) {
            this[this.cursor.y].splice(this.cursor.x, 0, this.cursor.attrs);
            this[this.cursor.y].pop();
        }
    },
    delete_characters: function(count) {
        count = Math.min(this.columns - this.cursor.x, count || 1);
        for (var i = 0; i < count; i++) {
            this[this.cursor.y].splice(this.cursor.x, 1);
            this[this.cursor.y].push(this.cursor.attrs);
        }
    },
    erase_characters: function(count) {
        count = count || 1;
        var max_pos = Math.min(this.cursor.x + count, this.columns);

        for (var column = this.cursor.x; column < max_pos; column++) {
            this[this.cursor.y][column] = this.cursor.attrs;
        }
    },
    erase_in_line: function(type_of) {
        type_of = type_of || 0;

        var interval = [
            range(this.cursor.x, this.columns),
            range(0, this.cursor.x + 1),
            range(0, this.columns)
        ][type_of];

        var column;
        for (var i = 0; i < interval.length; i++) {
            column = interval[i];
            this[this.cursor.y][column] = this.cursor.attrs;
        }
    },
    erase_in_display: function(type_of) {
        type_of = type_of || 0;

        var interval = [
            range(this.cursor.y + 1, this.lines),
            range(0, this.cursor.y),
            range(0, this.lines)
        ][type_of];

        var line;
        for (var i = 0; i < interval.length; i++) {
            line = interval[i];
            this[line] = repeat(this.columns, this.cursor.attrs);
        }

        if (type_of == 0 || type_of == 1) {
            this.erase_in_line(type_of);
        }
    },
    set_tab_stop: function() {
        this.tabstops[this.cursor.x] = true;
    },
    clear_tab_stop: function(type_of) {
        if (!type_of) {
            delete this.tabstops[this.cursor.x];
        } else if (type_of == 3) {
            this.tabstops = {};
        }
    },
    ensure_bounds: function(use_margins) {
        var top, bottom;
        if (use_margins || this.mode[DECOM]) {
            top = this.margins.top;
            bottom = this.margins.bottom;
        } else {
            top = 0;
            bottom = this.lines - 1;
        }

        this.cursor.x = Math.min(Math.max(0, this.cursor.x), this.columns - 1);
        this.cursor.y = Math.min(Math.max(top, this.cursor.y), bottom);
    },
    cursor_up: function(count) {
        this.cursor.y -= count || 1;
        this.ensure_bounds(true);
    },
    cursor_up1: function(count) {
        this.cursor_up(count);
        this.carriage_return();
    },
    cursor_down: function(count) {
        this.cursor.y += count || 1;
        this.ensure_bounds(true);
    },
    cursor_down1: function(count) {
        this.cursor_down(count);
        this.carriage_return();
    },
    cursor_back: function(count) {
        this.cursor.x -= count || 1;
        this.ensure_bounds();
    },
    cursor_forward: function(count) {
        this.cursor.x += count || 1;
        this.ensure_bounds();
    },
    cursor_position: function(line, column) {
        column = (column || 1) - 1;
        line = (line || 1) - 1;

        if (this.mode[DECOM]) {
            line += this.margins.top;

            if (!(this.margins.top <= line && line <= this.margins.bottom)) {
                return;
            }
        }

        this.cursor.x = column;
        this.cursor.y = line;
        this.ensure_bounds();
    },
    cursor_to_column: function(column) {
        this.cursor.x = (column || 1) - 1;
        this.ensure_bounds();
    },
    cursor_to_line: function(line) {
        this.cursor.y = (line || 1) - 1;

        if (this.mode[DECOM]) {
            this.cursor.y += this.margins.top;
        }

        this.ensure_bounds();
    },
    bell: function() {
        var el = document.getElementById('bell');
        if (el && el.tagName == 'AUDIO') el.play();
    },
    select_graphic_rendition: function() {
        var replace = {};
        var attrs = arguments || [0], attr;

        for (var i = 0; i < attrs.length; i++) {
            attr = attrs[i];

            if (FG[attr]) {
                replace["fg"] = FG[attr];
            } else if (BG[attr]) {
                replace["bg"] = BG[attr];
            } else if (TEXT[attr]) {
                attr = TEXT[attr];
                replace[attr.substr(1, attr.length - 1)] = attr.charAt(0)=="+";
            } else if (!attr) {
                replace = new Char(this.default_char.data, this.default_char);
            }
        }
        var curs = this.cursor;

        var newAttrs = new Char(curs.attrs.data, curs.attrs);
        for (var k in replace) newAttrs[k] = replace[k];
        curs.attrs = newAttrs;
    }
};