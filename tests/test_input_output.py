import json
import os.path, sys

import pytest

import pyte


captured_dir = os.path.join(os.path.dirname(__file__), "captured")

sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))
from asserts import consistency_asserts

@pytest.mark.parametrize("name", [
    "cat-gpl3", "find-etc", "htop", "ls", "mc", "top", "vi"
])
def test_input_output(name):
    with open(os.path.join(captured_dir, name + ".input"), "rb") as handle:
        input = handle.read()

    with open(os.path.join(captured_dir, name + ".output")) as handle:
        output = json.load(handle)

    screen = pyte.Screen(80, 24)
    stream = pyte.ByteStream(screen)
    stream.feed(input)
    assert screen.display == output
    consistency_asserts(screen)

@pytest.mark.parametrize("name", [
    "cat-gpl3", "find-etc", "htop", "ls", "mc", "top", "vi"
])
def test_input_output_history(name):
    with open(os.path.join(captured_dir, name + ".input"), "rb") as handle:
        input = handle.read()

    with open(os.path.join(captured_dir, name + ".output")) as handle:
        output = json.load(handle)

    screen = pyte.HistoryScreen(80, 24, history=72)
    stream = pyte.ByteStream(screen)
    stream.feed(input)
    screen.prev_page()
    screen.prev_page()
    screen.prev_page()
    screen.next_page()
    screen.next_page()
    screen.next_page()
    assert screen.display == output
    consistency_asserts(screen)
