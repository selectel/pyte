/*
    pyte.escape
    ~~~~~~~~~~~

    This module defines bot CSI and non-CSI escape sequences, recognized
    by :class:`~pyte.streams.Stream` and subclasses.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
*/


//: *Reset*.
var RIS = "c";

//: *Index*: Move cursor down one line in same column. If the cursor is
//: at the bottom margin, the screen performs a scroll-up.
var IND = "D";

//: *Next line*: Same as :data:`pyte.control.LF`.
var NEL = "E";

//: Tabulation set: Set a horizontal tab stop at cursor position.
var HTS = "H";

//: *Reverse index*: Move cursor up one line in same column. If the
//: cursor is at the top margin, the screen performs a scroll-down.
var RI = "M";

//: Save cursor: Save cursor position, character attribute (graphic
//: rendition), character set, and origin mode selection (see
//: :data:`DECRC`).
var DECSC = "7";

//: *Restore cursor*: Restore previously saved cursor position, character
//: attribute (graphic rendition), character set, and origin mode
//: selection. If none were saved, move cursor to home position.
var DECRC = "8";


// "Sharp" escape sequences.
// -------------------------

//: *Alignment display*: Fill screen with uppercase E's for testing
//: screen focus and alignment.
var DECALN = "8";


// ECMA-48 CSI sequences.
// ---------------------

//: *Insert character*: Insert the indicated // of blank characters.
var ICH = "@";

//: *Cursor up*: Move cursor up the indicated // of lines in same column.
//: Cursor stops at top margin.
var CUU = "A";

//: *Cursor down*: Move cursor down the indicated // of lines in same
//: column. Cursor stops at bottom margin.
var CUD = "B";

//: *Cursor forward*: Move cursor right the indicated // of columns.
//: Cursor stops at right margin.
var CUF = "C";

//: *Cursor back*: Move cursor left the indicated // of columns. Cursor
//: stops at left margin.
var CUB = "D";

//: *Cursor next line*: Move cursor down the indicated // of lines to
//: column 1.
var CNL = "E";

//: *Cursor previous line*: Move cursor up the indicated // of lines to
//: column 1.
var CPL = "F";

//: *Cursor horizontal align*: Move cursor to the indicated column in
//: current line.
var CHA = "G";

//: *Cursor position*: Move cursor to the indicated line, column (origin
//: at ``1, 1``).
var CUP = "H";

//: *Erase data* (default: from cursor to end of line).
var ED = "J";

//: *Erase in line* (default: from cursor to end of line).
var EL = "K";

//: *Insert line*: Insert the indicated // of blank lines, starting from
//: the current line. Lines displayed below cursor move down. Lines moved
//: past the bottom margin are lost.
var IL = "L";

//: *Delete line*: Delete the indicated // of lines, starting from the
//: current line. As lines are deleted, lines displayed below cursor
//: move up. Lines added to bottom of screen have spaces with same
//: character attributes as last line move up.
var DL = "M";

//: *Delete character*: Delete the indicated // of characters on the
//: current line. When character is deleted, all characters to the right
//: of cursor move left.
var DCH = "P";

//: *Erase character*: Erase the indicated // of characters on the
//: current line.
var ECH = "X";

//: *Horizontal position relative*: Same as :data:`CUF`.
var HPR = "a";

//: *Vertical position adjust*: Move cursor to the indicated line,
//: current column.
var VPA = "d";

//: *Vertical position relative*: Same as :data:`CUD`.
var VPR = "e";

//: *Horizontal / Vertical position*: Same as :data:`CUP`.
var HVP = "f";

//: *Tabulation clear*: Clears a horizontal tab stop at cursor position.
var TBC = "g";

//: *Set mode*.
var SM = "h";

//: *Reset mode*.
var RM = "l";

//: *Select graphics rendition*: The terminal can display the following
//: character attributes that change the character display without
//: changing the character (see :mod:`pyte.graphics`).
var SGR = "m";

//: *Select top and bottom margins*: Selects margins, defining the
//: scrolling region; parameters are top and bottom line. If called
//: without any arguments, whole screen is used.
var DECSTBM = "r";

//: *Horizontal position adjust*: Same as :data:`CHA`.
var HPA = "'";
