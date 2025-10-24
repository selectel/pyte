# Cursor Positioning Investigation Report

**Date:** 2025-10-24
**Investigator:** Claude Sonnet 4.5 + Alex
**Issue:** Gemini CLI cursor appears in wrong location in ActCLI-Bench (pyte-based) but works correctly in real terminals

---

## Executive Summary

**Problem Statement:**
- Gemini CLI works correctly in real terminals (xterm, iTerm2, etc.)
- Gemini CLI cursor appears on wrong line in ActCLI-Bench using pyte
- After typing 'x', cursor should be on input line but appears 3+ lines below

**Critical Question:**
If pyte is following ANSI standards correctly, why does Gemini work in real terminals? What are real terminals doing differently?

**Status:** Investigation incomplete - need to capture FULL escape sequence including any cursor positioning codes sent AFTER UI output.

---

## Methodology

### Test Environment
- **Pyte version:** 0.8.3.dev0 (installed from fork in editable mode)
- **Python:** 3.12
- **Test scenarios:**
  1. Simple sequence (empty screen → draw text)
  2. Complex sequence (pre-existing content → redraw)
  3. Full Gemini sequence (20 lines content → 6x clear+up → redraw 5 lines)

### Test Files Created
1. `diagnose_pyte_bug.py` - Simple sequence test
2. `test_full_gemini_sequence.py` - Complex pre-existing content test
3. `test_debug_cursor.py` - Step-by-step cursor movement debugging

---

## Findings

### Finding 1: Pyte Correctly Processes Simple Sequences

**Test:** `diagnose_pyte_bug.py`

**Input:**
```
ESC[2K (clear line)
ESC[1A (up) × 6
ESC[G (column 1)
\r\n (newline)
'│ > x' (draw text)
```

**Result:**
```
✅ Text at line 1: '│ > x'
✅ Cursor at: (5, 1)
✅ Cursor is at CORRECT position!
```

**Analysis:** On an empty screen, pyte correctly tracks cursor position. After drawing '│ > x' (5 characters), cursor is at column 5, line 1. ✅

---

### Finding 2: Pyte Cursor Position After Multi-Line Output

**Test:** `test_debug_cursor.py`

**Scenario:**
1. Create 20 lines of content → cursor at line 20
2. Clear + up 6 times → cursor at line 14 ✅
3. `\r\n` → cursor at line 15 ✅
4. Output 5 lines with `\r\n`:
   - Line 1: ` Using: 1 test.md file\r\n` → cursor to line 16
   - Line 2: `╭───...╮\r\n` → cursor to line 17
   - Line 3: `│ > x...│\r\n` → cursor to line 18 ⚠️
   - Line 4: `╰───...╯\r\n` → cursor to line 19
   - Line 5: `~/Projects/test\r\n` → cursor to line 20

**Result:**
```
✓ Text '│ > x' is at line: 17
✓ Cursor is at line: 20
❌ BUG: Cursor is 3 lines away from the text!
```

**Analysis:**
- **Pyte is following ANSI standard:** Each `\r\n` moves cursor down one line
- **After 5 lines with `\r\n`, cursor SHOULD be 3 lines below the input line**
- **This is CORRECT behavior** according to ANSI escape code semantics

---

### Finding 3: Troubleshooting Log Shows Truncated Escape Sequences

**Source:** `troubleshooting_pack_20251022T222932Z.txt` line 43

**Captured escape sequence:**
```
[feed] Received escape sequences: b'\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[1A\x1b[2K\x1b[G\r\n \x1b[38;2;108;112;134mUsing: 1 GEMINI.md file\x1b[39m\r\n\x1b[38;2;137;180;250m\xe2\x95\xad\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94'
```

**Observation:**
- Log is truncated at 200 bytes (see `term_emulator.py:103`)
- We only see the BEGINNING of the escape sequence
- **We don't see what comes AFTER the full UI output!**

**Critical Question:**
Does Gemini send cursor positioning codes (like `ESC[17;5H`) AFTER the UI output to reposition the cursor back to the input line?

---

### Finding 4: Real Terminal Behavior (Hypothesis)

**Hypothesis 1: Cursor Positioning Codes After Output**

Gemini might be sending:
```
[Output 5 lines with \r\n]
ESC[17;5H  ← Move cursor to line 17, column 5 (after '│ > x')
```

These codes would be:
- ✅ Present in real terminal output (xterm.js captures them)
- ❌ Truncated in our troubleshooting logs
- ❌ Never reaching pyte if truncated or lost

**Hypothesis 2: Terminal Mode Differences**

Real terminals might have modes enabled that we don't:
- `DECTCEM` - Cursor visibility
- `DECAWM` - Auto-wrap mode
- `DECOM` - Origin mode
- Others?

**Hypothesis 3: xterm.js Has Custom Cursor Handling**

xterm.js (used by real browser terminals) might:
- Automatically reposition cursor to last non-blank character
- Have special handling for TUI applications
- Track cursor differently than ANSI-only implementations

---

## Evidence Gap: We Don't Have Complete Picture

### What We Know:
✅ Pyte processes the captured escape sequences correctly
✅ The captured sequences don't contain cursor positioning back to input line
✅ Gemini works in real terminals

### What We DON'T Know:
❌ Complete escape sequence output from Gemini (logs truncated at 200 bytes)
❌ Whether Gemini sends cursor positioning codes after the UI
❌ What real terminals (xterm, iTerm2) actually receive from Gemini
❌ Whether there are terminal modes affecting cursor behavior

---

## Next Steps Required

### 1. Capture Complete Escape Sequences ⭐ CRITICAL

**Action:** Remove or increase the 200-byte truncation limit in `term_emulator.py:103`

**Current code:**
```python
preview = repr(b[:200]) if len(b) > 200 else repr(b)
self._debug_logger(f"[feed] Received escape sequences: {preview}")
```

**Needed:**
```python
# Log COMPLETE escape sequences, no truncation
self._debug_logger(f"[feed] Received escape sequences: {repr(b)}")
```

**Expected outcome:**
- See if Gemini sends `ESC[row;colH` cursor positioning after UI output
- Determine if pyte is receiving incomplete data

### 2. Compare Real Terminal vs Pyte

**Action:** Run Gemini in a real terminal with escape sequence logging

**Tools:**
- `script -f output.log` - Capture complete terminal session
- `cat -v output.log` - View escape sequences
- Compare byte-for-byte with pyte's input

**Expected outcome:**
- Identify any escape sequences that real terminals receive but pyte doesn't

### 3. Test xterm.js Behavior

**Action:** Create minimal HTML page with xterm.js and feed it identical sequences

**Test:**
```html
<script>
const term = new Terminal();
term.write('\x1b[2K\x1b[1A...'); // Our exact sequence
console.log('Cursor position:', term.buffer.active.cursorY);
</script>
```

**Expected outcome:**
- Determine if xterm.js has special cursor handling
- See if it behaves like pyte or differently

### 4. Check Terminal Modes

**Action:** Log pyte's active modes when Gemini is running

**Code:**
```python
# In term_emulator.py after feeding escape sequences
self._debug_logger(f"Active modes: {self._screen.mode}")
```

**Expected outcome:**
- Identify if any terminal modes affect cursor positioning
- Check if modes differ from real terminal expectations

---

## Test Data Summary

### Test 1: Simple Sequence (Empty Screen)
| Metric | Value | Status |
|--------|-------|--------|
| Input text | '│ > x' | - |
| Expected cursor | (5, 1) | - |
| Actual cursor | (5, 1) | ✅ PASS |
| Conclusion | Pyte works correctly on empty screen | ✅ |

### Test 2: Full Sequence (Pre-existing Content)
| Metric | Value | Status |
|--------|-------|--------|
| Initial cursor | (0, 20) | - |
| After 6x up | (0, 14) | ✅ |
| After \r\n | (0, 15) | ✅ |
| After 5 lines output | (0, 20) | ✅ |
| Text '│ > x' at line | 17 | - |
| Cursor at line | 20 | ⚠️ |
| Lines away from text | 3 | ❌ BUG |

### Test 3: Real Gemini in ActCLI-Bench (from troubleshooting log)
| Metric | Value | Status |
|--------|-------|--------|
| Screen size | 175x51 | - |
| Cursor position | (0, 21) | - |
| Expected (visual) | Line with '│ > x' | - |
| Actual | Blank line | ❌ BUG |
| Escape sequences captured | Truncated at 200 bytes | ⚠️ INCOMPLETE |

---

## Conclusions

### What We've Proven:
1. ✅ **Pyte correctly implements ANSI escape code standards**
   - Cursor movement commands work as specified
   - Text drawing advances cursor appropriately
   - Line feeds (`\r\n`) move cursor down correctly

2. ✅ **The captured escape sequences lead to the observed cursor position**
   - Following the logged sequences, cursor at line 20 is correct
   - This matches pyte's actual behavior

3. ⚠️ **We have incomplete data**
   - Escape sequences are truncated in logs
   - We don't see what Gemini sends AFTER the UI output
   - Cannot determine if cursor positioning codes are present

### What We HAVEN'T Proven:
1. ❌ **Whether pyte is buggy or just different from real terminals**
   - Need to see complete escape sequences from real terminal
   - Need to compare byte-for-byte with what pyte receives

2. ❌ **Why Gemini works in real terminals**
   - Don't know if xterm.js has special cursor handling
   - Don't know if additional escape codes are sent
   - Don't know if terminal modes play a role

3. ❌ **Whether ActCLI-TE would have the same issue**
   - If following ANSI standards strictly, yes
   - If adding xterm.js-style special handling, maybe not
   - Need more data to determine requirements

---

## Critical Blocker

**We cannot proceed with patching pyte until we answer:**

> **"What does a real terminal receive from Gemini that we're not seeing?"**

The current troubleshooting logs truncate at 200 bytes, cutting off potentially critical cursor positioning codes that would explain why Gemini works in real terminals.

**Recommendation:** Before forking pyte or building ActCLI-TE, we must:
1. Capture complete, untruncated escape sequences
2. Run identical sequence through real terminal and compare
3. Determine if pyte is genuinely buggy or just strictly following ANSI standards

---

## Open Questions for Discussion

1. **Should we capture complete escape sequences first?**
   - Modify `term_emulator.py` to remove 200-byte truncation
   - Re-run Gemini and capture full output
   - Look for cursor positioning codes after UI output

2. **Is the "bug" actually in pyte, or in our expectations?**
   - If Gemini sends `ESC[row;colH` after output, pyte should handle it
   - If Gemini doesn't send cursor codes, should pyte "guess" where cursor should be?
   - Real terminals might have browser-level cursor handling we can't replicate

3. **What should ActCLI-TE do?**
   - Follow ANSI standards strictly (like pyte)? → Same bug
   - Add special TUI cursor handling? → Deviates from standards
   - Copy xterm.js behavior exactly? → Complex, but might work

4. **Is pattern-matching the right approach for ActCLI-Bench?**
   - Current `_find_input_line()` method works around cursor issues
   - Maybe this is the correct solution for terminal emulators?
   - Real terminals might have similar heuristics

---

## Appendix A: Code References

### Pyte Methods Examined
- `screens.py:493` - `draw()` - Character drawing and cursor advancement
- `screens.py:574` - `carriage_return()` - Move cursor to column 0
- `screens.py:606` - `linefeed()` - Move cursor down (calls `index()`)
- `screens.py:578` - `index()` - Move down or scroll
- `screens.py:873` - `cursor_up()` - Move cursor up with margin handling

All methods appear to correctly implement ANSI X3.64 / ECMA-48 standards.

### ActCLI-Bench Code
- `term_emulator.py:103` - **200-byte truncation of escape sequences**
- `term_emulator.py:253` - `text_with_cursor()` - Uses pyte cursor position
- `term_emulator.py:158` - `_find_input_line()` - Pattern matching workaround

### Test Files
- `diagnose_pyte_bug.py` - Simple sequence (passes ✅)
- `test_full_gemini_sequence.py` - Complex sequence (fails ❌)
- `test_debug_cursor.py` - Step-by-step debugging (shows expected behavior)

---

## Appendix B: Escape Sequence Reference

| Code | Meaning | Pyte Support |
|------|---------|--------------|
| `ESC[2K` | Clear entire line | ✅ |
| `ESC[1A` | Cursor up 1 line | ✅ |
| `ESC[G` | Cursor to column 1 | ✅ |
| `\r` | Carriage return | ✅ |
| `\n` | Line feed | ✅ |
| `ESC[row;colH` | Cursor position (absolute) | ✅ |
| `ESC[38;2;r;g;bm` | RGB foreground color | ✅ |
| `ESC[39m` | Default foreground | ✅ |

All tested escape codes work correctly in pyte.

---

**End of Report**

*Next action: Team discussion on whether to capture complete escape sequences or pursue alternative approach.*
