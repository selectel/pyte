#!/usr/bin/env python3
"""Debug cursor movement step-by-step to find the bug."""

import pyte

def print_state(screen, label):
    """Print cursor state and nearby lines."""
    print(f"\n{label}")
    print(f"  Cursor: ({screen.cursor.x}, {screen.cursor.y})")

    # Show lines with content
    for i in range(max(0, screen.cursor.y - 2), min(screen.lines, screen.cursor.y + 5)):
        line = screen.display[i]
        marker = " ← CURSOR" if i == screen.cursor.y else ""
        if line.strip() or marker:
            print(f"  Line {i:2d}: {repr(line[:60])}{marker}")

def main():
    print("="*80)
    print("DEBUG: Cursor Movement After Up + Clear Sequence")
    print("="*80)

    # Use larger screen to match real scenario
    screen = pyte.Screen(175, 51)
    stream = pyte.ByteStream(screen)

    # Simulate some initial content (fill up to line 20)
    print("\n[STEP 1] Create initial content (20 lines)")
    for i in range(20):
        stream.feed(f"Line {i}\r\n".encode())

    print_state(screen, "After initial content:")

    # Now do the clear + up sequence (6 times)
    print("\n[STEP 2] Clear current line and move up 6 times")
    stream.feed(b'\x1b[2K')  # Clear line
    print_state(screen, "After clear:")

    for i in range(6):
        stream.feed(b'\x1b[1A\x1b[2K')  # Up + clear
        print_state(screen, f"After up #{i+1}:")

    # Move to column 1
    stream.feed(b'\x1b[G')
    print_state(screen, "After ESC[G (column 1):")

    # Carriage return + newline
    stream.feed(b'\r')
    print_state(screen, "After \\r:")

    stream.feed(b'\n')
    print_state(screen, "After \\n:")

    # Output the content
    print("\n[STEP 3] Output new content")
    stream.feed(b' Using: 1 test.md file\r\n')
    print_state(screen, "After line 1:")

    stream.feed(b'\xe2\x95\xad' + b'\xe2\x94\x80'*40 + b'\xe2\x95\xae\r\n')
    print_state(screen, "After line 2 (box top):")

    stream.feed(b'\xe2\x94\x82 > x                                    \xe2\x94\x82\r\n')
    print_state(screen, "After line 3 (input with 'x'):")

    stream.feed(b'\xe2\x95\xb0' + b'\xe2\x94\x80'*40 + b'\xe2\x95\xaf\r\n')
    print_state(screen, "After line 4 (box bottom):")

    stream.feed(b'~/Projects/test\r\n')
    print_state(screen, "After line 5 (path):")

    # Find where the text actually is
    print("\n" + "="*80)
    print("FINAL ANALYSIS")
    print("="*80)

    text_line = None
    for i, line in enumerate(screen.display):
        if '> x' in line:
            text_line = i
            print(f"✓ Text '> x' found at line: {i}")
            print(f"  Content: {repr(line[:60])}")
            break

    if text_line is None:
        print("❌ ERROR: Could not find '> x' in output!")
    else:
        print(f"\n✓ Cursor is at line: {screen.cursor.y}")
        print(f"✓ Text is at line: {text_line}")

        if screen.cursor.y == text_line:
            print("\n✅ SUCCESS: Cursor is on the same line as the text!")
        else:
            diff = screen.cursor.y - text_line
            print(f"\n❌ BUG: Cursor is {diff} lines away from the text!")
            print(f"   Cursor should be on line {text_line}, but it's on line {screen.cursor.y}")

if __name__ == '__main__':
    main()
