import json
import os.path

import pytest

import pyte


captured_dir = os.path.join(os.path.dirname(__file__), "captured")


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
