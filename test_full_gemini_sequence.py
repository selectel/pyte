#!/usr/bin/env python3
"""Test the FULL Gemini sequence including initial box output.

This reproduces the exact scenario from pyte_cursor_investigation.py
where the cursor ends up on line 9 instead of line 6.
"""

import pyte

def main():
    print("="*80)
    print("FULL GEMINI SEQUENCE TEST - With Initial UI Box")
    print("="*80)

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    # Step 1: Initial Gemini output (creates the UI box)
    print("\n[STEP 1] Initial Gemini output (UI box)")
    initial_sequence = (
        b"Loaded cached credentials.\r\n" +
        b"\r\n" +
        b"\xe2\x95\xad" +  # ╭
        b"\xe2\x94\x80"*40 +  # ────...
        b"\xe2\x95\xae\r\n" +  # ╮
        b"\xe2\x94\x82 > Type your message                    \xe2\x94\x82\r\n" +  # │...│
        b"\xe2\x95\xb0" +  # ╰
        b"\xe2\x94\x80"*40 +  # ────...
        b"\xe2\x95\xaf\r\n" +  # ╯
        b"~/Projects/test                          \r\n"
    )
    stream.feed(initial_sequence)

    print(f"After initial output:")
    print(f"  Cursor: ({screen.cursor.x}, {screen.cursor.y})")
    for i, line in enumerate(screen.display):
        if line.strip():
            print(f"  Line {i}: {repr(line[:60])}")

    # Step 2: Type 'x' - Gemini's redraw pattern
    print("\n[STEP 2] User types 'x' - Gemini redraws entire UI")
    redraw_sequence = (
        b"\x1b[2K" +  # Clear current line
        b"\x1b[1A\x1b[2K" +  # Up and clear
        b"\x1b[1A\x1b[2K" +  # Up and clear
        b"\x1b[1A\x1b[2K" +  # Up and clear
        b"\x1b[1A\x1b[2K" +  # Up and clear
        b"\x1b[1A\x1b[2K" +  # Up and clear
        b"\x1b[1A\x1b[2K" +  # Up and clear
        b"\x1b[G" +  # Move to column 1
        b"\r\n" +
        b" Using: 1 test.md file\r\n" +
        b"\xe2\x95\xad" +  # ╭
        b"\xe2\x94\x80"*40 +  # ────...
        b"\xe2\x95\xae\r\n" +  # ╮
        b"\xe2\x94\x82 > x                                    \xe2\x94\x82\r\n" +  # │ > x│
        b"\xe2\x95\xb0" +  # ╰
        b"\xe2\x94\x80"*40 +  # ────...
        b"\xe2\x95\xaf\r\n" +  # ╯
        b"~/Projects/test                          \r\n"
    )
    stream.feed(redraw_sequence)

    print(f"\nAfter redraw with 'x':")
    print(f"  Cursor: ({screen.cursor.x}, {screen.cursor.y})")

    # Find where the text actually is
    text_line = None
    for i, line in enumerate(screen.display):
        if '│ > x' in line or '> x' in line:
            text_line = i
            print(f"  Text found at line {i}: {repr(line[:60])}")
            break

    print(f"\n{'='*80}")
    print("ANALYSIS")
    print("="*80)
    if text_line is not None:
        print(f"✓ Text '│ > x' is at line: {text_line}")
        print(f"✓ Cursor is at: ({screen.cursor.x}, {screen.cursor.y})")

        if screen.cursor.y == text_line:
            print(f"\n✅ SUCCESS: Cursor is on the CORRECT line!")
        else:
            print(f"\n❌ BUG: Cursor is on line {screen.cursor.y}, but text is on line {text_line}")
            print(f"   Cursor is {abs(screen.cursor.y - text_line)} lines away from the text!")
            print(f"   Line {screen.cursor.y}: {repr(screen.display[screen.cursor.y][:60])}")
    else:
        print("❌ ERROR: Could not find '│ > x' in output!")

    print(f"\n{'='*80}")
    print("FULL SCREEN DUMP")
    print("="*80)
    for i, line in enumerate(screen.display):
        if line.strip():
            marker = " ← CURSOR" if i == screen.cursor.y else ""
            print(f"  Line {i:2d}: {repr(line[:60])}{marker}")

if __name__ == '__main__':
    main()
