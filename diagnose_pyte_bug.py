#!/usr/bin/env python3
"""Diagnostic tool to pinpoint the pyte cursor bug.

This script feeds Gemini's exact escape sequence to pyte step-by-step
and shows where the cursor position diverges from expected behavior.

Run this BEFORE and AFTER your fix to validate the patch.
"""

import sys
try:
    import pyte
except ImportError:
    print("ERROR: pyte not installed. Run: pip install pyte")
    sys.exit(1)


def print_screen_state(screen, label):
    """Print current screen state with cursor position."""
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")
    print(f"Cursor position: ({screen.cursor.x}, {screen.cursor.y})")
    print(f"Screen size: {screen.columns}x{screen.lines}")

    # Show lines around cursor
    start = max(0, screen.cursor.y - 2)
    end = min(screen.lines, screen.cursor.y + 3)

    print("\nScreen content (lines around cursor):")
    for i in range(start, end):
        line = screen.display[i]
        marker = " ← CURSOR" if i == screen.cursor.y else ""
        # Show first 60 chars to fit in terminal
        line_preview = line[:60].rstrip()
        if line_preview:
            print(f"  Line {i:2d}: {repr(line_preview)}{marker}")
        else:
            print(f"  Line {i:2d}: [empty]{marker}")


def test_step_by_step():
    """Run Gemini sequence step-by-step with diagnostics."""

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    print("PYTE CURSOR BUG DIAGNOSTIC")
    print("="*70)
    print("Testing Gemini AI CLI redraw pattern")
    print()

    # Initial state
    print_screen_state(screen, "STEP 0: Initial state")

    # Step 1: Multiple clear + up sequences
    print_screen_state(screen, "STEP 1: After first clear line (ESC[2K)")
    stream.feed(b'\x1b[2K')
    print_screen_state(screen, "After clear")

    stream.feed(b'\x1b[1A')
    print_screen_state(screen, "STEP 2: After move up (ESC[1A)")

    # Repeat clear+up pattern (Gemini does this 6 times)
    for i in range(5):
        stream.feed(b'\x1b[2K\x1b[1A')
    print_screen_state(screen, f"STEP 3: After 5 more clear+up sequences")

    # Move to column 1
    stream.feed(b'\x1b[G')
    print_screen_state(screen, "STEP 4: After move to column 1 (ESC[G)")

    # Carriage return + newline
    stream.feed(b'\r')
    print_screen_state(screen, "STEP 5: After carriage return (\\r)")

    stream.feed(b'\n')
    print_screen_state(screen, "STEP 6: After newline (\\n)")

    # Draw the actual content
    stream.feed(b'\xe2\x94\x82 > x')
    print_screen_state(screen, "STEP 7: After drawing '│ > x'")

    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)

    # Find the line with content
    text_line = None
    for i, line in enumerate(screen.display):
        if '│ > x' in line or '> x' in line:
            text_line = i
            break

    if text_line is None:
        print("❌ ERROR: Could not find output '│ > x' in screen!")
        print("\nFull screen dump:")
        for i, line in enumerate(screen.display):
            if line.strip():
                print(f"  Line {i}: {repr(line[:60])}")
        return False

    print(f"✓ Text found at line: {text_line}")
    print(f"✓ Text content: {repr(screen.display[text_line][:20])}")

    # Check cursor position
    expected_x = 5  # After '│ > x' (5 characters, cursor at next position)
    expected_y = text_line

    actual_x = screen.cursor.x
    actual_y = screen.cursor.y

    print(f"\nExpected cursor: ({expected_x}, {expected_y})")
    print(f"Actual cursor:   ({actual_x}, {actual_y})")

    if actual_x == expected_x and actual_y == expected_y:
        print("\n✅ SUCCESS: Cursor is at correct position!")
        print("   The pyte fix is working!")
        return True
    else:
        print("\n❌ FAILURE: Cursor is at WRONG position!")
        print(f"   Expected: cursor after 'x' at column {expected_x}, line {text_line}")
        print(f"   Actual: cursor at column {actual_x}, line {actual_y}")

        if actual_y != expected_y:
            print(f"\n   🐛 BUG: Cursor is on line {actual_y} instead of {expected_y}")
            print(f"       Line {actual_y} content: {repr(screen.display[actual_y][:40])}")

        if actual_x != expected_x:
            print(f"\n   🐛 BUG: Cursor is at column {actual_x} instead of {expected_x}")

        print("\n   This is the bug that needs to be fixed!")
        return False


def test_complete_sequence():
    """Test the complete sequence as one block."""
    print("\n\n" + "="*70)
    print("COMPLETE SEQUENCE TEST (all at once)")
    print("="*70)

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)

    # Full Gemini sequence
    sequence = (
        b'\x1b[2K\x1b[1A'  # Clear + up
        b'\x1b[2K\x1b[1A'  # Clear + up
        b'\x1b[2K\x1b[1A'  # Clear + up
        b'\x1b[2K\x1b[1A'  # Clear + up
        b'\x1b[2K\x1b[1A'  # Clear + up
        b'\x1b[2K\x1b[1A'  # Clear + up
        b'\x1b[G'          # Column 1
        b'\r\n'            # Newline
        b'\xe2\x94\x82 > x'  # "│ > x"
    )

    stream.feed(sequence)

    # Find text line
    text_line = None
    for i, line in enumerate(screen.display):
        if '│ > x' in line or '> x' in line:
            text_line = i
            break

    if text_line is None:
        print("❌ Could not find output")
        return False

    print(f"Text at line {text_line}: {repr(screen.display[text_line][:20])}")
    print(f"Cursor: ({screen.cursor.x}, {screen.cursor.y})")

    if screen.cursor.y == text_line and screen.cursor.x == 5:
        print("✅ SUCCESS: Complete sequence works!")
        return True
    else:
        print("❌ FAILURE: Complete sequence shows bug")
        return False


def main():
    """Run all diagnostic tests."""
    success = test_step_by_step()
    test_complete_sequence()

    print("\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if success:
        print("✅ All tests PASSED")
        print("   The cursor tracking fix is working correctly!")
        print("\nNext steps:")
        print("  1. Run full pyte test suite: pytest tests/")
        print("  2. Commit your changes")
        print("  3. Publish to PyPI as pyte-0.8.2+actcli.1")
    else:
        print("❌ Tests FAILED")
        print("   The cursor bug is still present.")
        print("\nDebugging hints:")
        print("  1. Check pyte/screens.py methods:")
        print("     - draw() - advances cursor after text")
        print("     - carriage_return() - moves to column 0")
        print("     - linefeed() - moves down")
        print("     - cursor_up() - moves up")
        print("  2. Look for where cursor position gets reset incorrectly")
        print("  3. The bug is likely in the interaction between these methods")
        print("\n  See the step-by-step output above to identify where it breaks!")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
