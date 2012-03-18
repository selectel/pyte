//: *Space*: Not suprisingly -- ``" "``.
var SP = " ";

//: *Null*: Does nothing.
var NUL = "\u0000";

//: *Bell*: Beeps.
var BEL = "\u0007";

//: *Backspace*: Backspace one column, but not past the begining of the
//: line.
var BS = "\u0008";

//: *Horizontal tab*: Move cursor to the next tab stop, or to the end
//: of the line if there is no earlier tab stop.
var HT = "\u0009";

//: *Linefeed*: Give a line feed, and, if :data:`pyte.modes.LNM` (new
//: line mode) is set also a carriage return.
var LF = "\n";
//: *Vertical tab*: Same as :data:`LF`.
var VT = "\u000b";
//: *Form feed*: Same as :data:`LF`.
var FF = "\u000c";

//: *Carriage return*: Move cursor to left margin on current line.
var CR = "\r";

//: *Shift out*: Activate G1 character set.
var SO = "\u000e";

//: *Shift in*: Activate G0 character set.
var SI = "\u000f";

//: *Cancel*: Interrupt escape sequence. If received during an escape or
//: control sequence, cancels the sequence and displays substitution
//: character.
var CAN = "\u0018";
//: *Substitute*: Same as :data:`CAN`.
var SUB = "\u001a";

//: *Escape*: Starts an escape sequence.
var ESC = "\u001b";

//: *Delete*: Is ingored.
var DEL = "\u007f";

//: *Control sequence introducer*: An equavalent for ``ESC [``.
var CSI = "\u009b";