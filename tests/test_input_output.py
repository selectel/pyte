# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
import os.path

import pytest

import pyte


captured_dir = os.path.join(os.path.dirname(__file__), "captured")


@pytest.mark.parametrize("name", [
    "cat-gpl3", "emacs-tetris", "find-etc", "htop-10s", "ls",
    "man-man", "mc", "top", "vi"
])
def test_input_output(name):
    with open(os.path.join(captured_dir, name + ".input"), "rb") as handle:
        input = handle.read()

    with open(os.path.join(captured_dir, name + ".output")) as handle:
        output = json.load(handle)

    screen = pyte.Screen(80, 24)
    stream = pyte.Stream(screen)
    stream.feed(input)
    assert screen.display == output
